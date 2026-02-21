import html
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.common import format_backups
from app.keyboards import backup_pro_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.backups import create_backup, delete_backup, list_backups, resolve_backup_name, restore_backup
from app.services.formatting import pre
from app.states import BotStates

router = Router()


@router.callback_query(F.data == "bpro:list")
async def backup_pro_list(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    items = list_backups(limit=30)
    await update_window_from_callback(callback, format_backups(items), backup_pro_menu())


@router.callback_query(F.data == "bpro:create")
async def backup_pro_create_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_backup_pro_source)
    await update_window_from_callback(callback, "<b>Создать backup</b>\nВведите абсолютный путь к папке:", backup_pro_menu())


@router.message(BotStates.waiting_backup_pro_source, F.text)
async def backup_pro_create_input(message: Message, state: FSMContext) -> None:
    source = Path(message.text.strip()).expanduser()
    if not source.is_absolute():
        await update_window_from_message(message, "<b>Создать backup</b>\nНужен абсолютный путь. Введите снова:", backup_pro_menu())
        await safe_delete(message)
        return
    if not source.exists() or not source.is_dir():
        await update_window_from_message(message, "<b>Создать backup</b>\nПапка не найдена. Введите снова:", backup_pro_menu())
        await safe_delete(message)
        return
    await state.clear()
    try:
        archive_path, size_bytes, checksum = await create_backup(source)
        text = (
            "<b>Backup создан</b>\n"
            f"<b>Источник:</b> <code>{html.escape(str(source))}</code>\n"
            f"<b>Архив:</b> <code>{html.escape(str(archive_path))}</code>\n"
            f"<b>Размер:</b> {size_bytes / 1024**2:.2f} MB\n"
            f"<b>SHA256:</b> <code>{checksum}</code>"
        )
    except Exception as exc:
        text = f"<b>Ошибка backup</b>\n{pre(str(exc), limit=900)}"
    await update_window_from_message(message, text, backup_pro_menu())
    await safe_delete(message)


@router.callback_query(F.data == "bpro:download")
async def backup_pro_download_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_backup_pro_download_name)
    items = list_backups(limit=10)
    await update_window_from_callback(callback, f"{format_backups(items)}\n\n<b>Введите имя архива для скачивания:</b>", backup_pro_menu())


@router.message(BotStates.waiting_backup_pro_download_name, F.text)
async def backup_pro_download_input(message: Message, state: FSMContext) -> None:
    archive = resolve_backup_name(message.text.strip())
    if not archive:
        await update_window_from_message(message, "<b>Скачать backup</b>\nАрхив не найден. Введите имя снова:", backup_pro_menu())
        await safe_delete(message)
        return
    await state.clear()
    try:
        await message.answer_document(FSInputFile(path=str(archive)), caption=archive.name)
        text = f"<b>Архив отправлен</b>\n<code>{html.escape(archive.name)}</code>"
    except Exception as exc:
        text = f"<b>Ошибка отправки</b>\n{pre(str(exc), limit=700)}"
    await update_window_from_message(message, text, backup_pro_menu())
    await safe_delete(message)


@router.callback_query(F.data == "bpro:restore")
async def backup_pro_restore_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_backup_pro_restore_archive)
    items = list_backups(limit=10)
    await update_window_from_callback(callback, f"{format_backups(items)}\n\n<b>Введите имя архива для восстановления:</b>", backup_pro_menu())


@router.message(BotStates.waiting_backup_pro_restore_archive, F.text)
async def backup_pro_restore_archive_input(message: Message, state: FSMContext) -> None:
    archive = resolve_backup_name(message.text.strip())
    if not archive:
        await update_window_from_message(message, "<b>Restore backup</b>\nАрхив не найден. Введите имя снова:", backup_pro_menu())
        await safe_delete(message)
        return
    await state.update_data(restore_archive=str(archive))
    await state.set_state(BotStates.waiting_backup_pro_restore_target)
    await update_window_from_message(
        message,
        f"<b>Архив:</b> <code>{html.escape(archive.name)}</code>\nВведите абсолютный путь папки назначения:",
        backup_pro_menu(),
    )
    await safe_delete(message)


@router.message(BotStates.waiting_backup_pro_restore_target, F.text)
async def backup_pro_restore_target_input(message: Message, state: FSMContext) -> None:
    target = Path(message.text.strip()).expanduser()
    if not target.is_absolute():
        await update_window_from_message(message, "<b>Restore backup</b>\nНужен абсолютный путь. Введите снова:", backup_pro_menu())
        await safe_delete(message)
        return
    data = await state.get_data()
    archive_raw = data.get("restore_archive")
    if not archive_raw:
        await state.clear()
        await update_window_from_message(message, "<b>Restore backup</b>\nАрхив не выбран. Начните заново.", backup_pro_menu())
        await safe_delete(message)
        return
    archive = Path(archive_raw)
    await state.clear()
    try:
        extracted = await restore_backup(archive, target)
        text = (
            "<b>Восстановление завершено</b>\n"
            f"<b>Архив:</b> <code>{html.escape(archive.name)}</code>\n"
            f"<b>Куда:</b> <code>{html.escape(str(target))}</code>\n"
            f"<b>Объектов:</b> {extracted}"
        )
    except Exception as exc:
        text = f"<b>Ошибка восстановления</b>\n{pre(str(exc), limit=900)}"
    await update_window_from_message(message, text, backup_pro_menu())
    await safe_delete(message)


@router.callback_query(F.data == "bpro:delete")
async def backup_pro_delete_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_backup_pro_delete_name)
    items = list_backups(limit=10)
    await update_window_from_callback(callback, f"{format_backups(items)}\n\n<b>Введите имя архива для удаления:</b>", backup_pro_menu())


@router.message(BotStates.waiting_backup_pro_delete_name, F.text)
async def backup_pro_delete_input(message: Message, state: FSMContext) -> None:
    archive = resolve_backup_name(message.text.strip())
    if not archive:
        await update_window_from_message(message, "<b>Удаление backup</b>\nАрхив не найден. Введите имя снова:", backup_pro_menu())
        await safe_delete(message)
        return
    ok, info = delete_backup(archive)
    await state.clear()
    if ok:
        text = f"<b>Архив удален</b>\n<code>{html.escape(archive.name)}</code>"
    else:
        text = f"<b>Ошибка удаления</b>\n{pre(info, limit=700)}"
    await update_window_from_message(message, text, backup_pro_menu())
    await safe_delete(message)
