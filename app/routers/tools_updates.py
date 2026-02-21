from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import Settings
from app.keyboards import updates_confirm_menu, updates_menu
from app.runtime import update_window_from_callback
from app.services.formatting import command_report
from app.services.shell import run_shell
from app.services.updates import (
    detect_package_manager,
    manager_title,
    updates_check_command,
    updates_cleanup_command,
    updates_upgrade_command,
)

router = Router()


@router.callback_query(F.data == "upd:check")
async def updates_check(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer("Проверяю...")
    await state.clear()
    manager = detect_package_manager()
    command = updates_check_command(manager)
    if not command:
        await update_window_from_callback(callback, "<b>Менеджер пакетов не поддерживается</b>", updates_menu())
        return
    result = await run_shell(command, timeout=max(settings.command_timeout, 900))
    await update_window_from_callback(callback, command_report(f"Проверка обновлений ({manager_title(manager)})", result), updates_menu())


@router.callback_query(F.data == "upd:upgrade")
async def updates_upgrade_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    manager = detect_package_manager()
    if not updates_upgrade_command(manager):
        await update_window_from_callback(callback, "<b>Менеджер пакетов не поддерживается</b>", updates_menu())
        return
    text = (
        "<b>Подтверждение upgrade</b>\n"
        f"Менеджер: <b>{manager_title(manager)}</b>\n"
        "Операция может занять длительное время."
    )
    await update_window_from_callback(callback, text, updates_confirm_menu())


@router.callback_query(F.data == "upd:upgrade:yes")
async def updates_upgrade_confirm(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer("Запускаю upgrade...")
    await state.clear()
    manager = detect_package_manager()
    command = updates_upgrade_command(manager)
    if not command:
        await update_window_from_callback(callback, "<b>Менеджер пакетов не поддерживается</b>", updates_menu())
        return
    result = await run_shell(command, timeout=max(settings.command_timeout, 5400))
    await update_window_from_callback(callback, command_report(f"Upgrade ({manager_title(manager)})", result), updates_menu())


@router.callback_query(F.data == "upd:clean")
async def updates_clean(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer("Очищаю...")
    await state.clear()
    manager = detect_package_manager()
    command = updates_cleanup_command(manager)
    if not command:
        await update_window_from_callback(callback, "<b>Менеджер пакетов не поддерживается</b>", updates_menu())
        return
    result = await run_shell(command, timeout=max(settings.command_timeout, 900))
    await update_window_from_callback(callback, command_report(f"Очистка кэша ({manager_title(manager)})", result), updates_menu())
