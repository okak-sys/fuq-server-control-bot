import html
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.common import normalize_heavy_files
from app.keyboards import backups_menu, files_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.backups import create_backup
from app.services.formatting import command_report, pre
from app.services.shell import run_shell
from app.states import BotStates
from app.config import Settings

router = Router()


@router.callback_query(F.data == "files:heavy")
async def files_heavy(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer("Сканирую файловую систему...")
    await state.clear()
    command = (
        "find / -xdev "
        "\\( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /tmp \\) -prune -o "
        "-type f -size +100M -printf '%s\\t%p\\n' 2>/dev/null | sort -nr | head -n 20"
    )
    result = await run_shell(command, timeout=max(settings.command_timeout, 120))
    if result.returncode == 0 and not result.stderr.strip():
        normalized = normalize_heavy_files(result.stdout)
        text = f"<b>ТОП тяжелых файлов (>100 MB)</b>\n{pre(normalized, limit=3200)}"
    else:
        text = command_report("ТОП тяжелых файлов", result)
    await update_window_from_callback(callback, text, files_menu())


@router.callback_query(F.data == "files:download")
async def files_download_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_download_path)
    await update_window_from_callback(callback, "<b>Скачать файл</b>\nВведите абсолютный путь к файлу:", files_menu())


@router.message(BotStates.waiting_download_path, F.text)
async def files_download_input(message: Message, state: FSMContext) -> None:
    raw_path = message.text.strip()
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        await update_window_from_message(message, "<b>Скачать файл</b>\nНужен абсолютный путь. Введите снова:", files_menu())
        await safe_delete(message)
        return
    if not path.exists() or not path.is_file():
        await update_window_from_message(message, "<b>Скачать файл</b>\nФайл не найден. Введите корректный путь:", files_menu())
        await safe_delete(message)
        return
    await state.clear()
    try:
        await message.answer_document(FSInputFile(path=str(path)), caption=path.name)
        size_mb = path.stat().st_size / 1024**2
        text = f"<b>Файл отправлен</b>\n<code>{html.escape(str(path))}</code>\n<b>Размер:</b> {size_mb:.2f} MB"
    except Exception as exc:
        text = f"<b>Ошибка отправки файла</b>\n{pre(str(exc), limit=600)}"
    await update_window_from_message(message, text, files_menu())
    await safe_delete(message)


@router.callback_query(F.data == "backup:create")
async def backup_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_backup_path)
    await update_window_from_callback(callback, "<b>Бэкап папки</b>\nВведите абсолютный путь к папке:", backups_menu())


@router.message(BotStates.waiting_backup_path, F.text)
async def backup_input(message: Message, state: FSMContext) -> None:
    source = Path(message.text.strip()).expanduser()
    if not source.is_absolute():
        await update_window_from_message(message, "<b>Бэкап папки</b>\nНужен абсолютный путь. Введите снова:", backups_menu())
        await safe_delete(message)
        return
    if not source.exists() or not source.is_dir():
        await update_window_from_message(message, "<b>Бэкап папки</b>\nПапка не найдена. Введите снова:", backups_menu())
        await safe_delete(message)
        return
    await state.clear()
    try:
        archive_path, size_bytes, checksum = await create_backup(source)
        text = (
            "<b>Бэкап завершен</b>\n"
            f"<b>Источник:</b> <code>{html.escape(str(source))}</code>\n"
            f"<b>Архив:</b> <code>{html.escape(str(archive_path))}</code>\n"
            f"<b>Размер:</b> {size_bytes / 1024**2:.2f} MB\n"
            f"<b>SHA256:</b> <code>{checksum[:16]}...</code>"
        )
    except Exception as exc:
        text = f"<b>Ошибка создания бэкапа</b>\n{pre(str(exc), limit=800)}"
    await update_window_from_message(message, text, backups_menu())
    await safe_delete(message)
