from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common import SERVICE_NAME_RE, parse_ip
from app.config import Settings
from app.keyboards import fail2ban_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.formatting import command_report
from app.services.shell import run_exec
from app.states import BotStates

router = Router()


@router.callback_query(F.data == "f2b:status")
async def f2b_status(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["fail2ban-client", "status"], timeout=settings.command_timeout)
    await update_window_from_callback(callback, command_report("fail2ban status", result), fail2ban_menu())


@router.callback_query(F.data == "f2b:jails")
async def f2b_jails(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["fail2ban-client", "status"], timeout=settings.command_timeout)
    await update_window_from_callback(callback, command_report("Список jail", result), fail2ban_menu())


@router.callback_query(F.data == "f2b:jail_status")
async def f2b_jail_status_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_f2b_jail_status)
    await update_window_from_callback(callback, "<b>Статус jail</b>\nВведите имя jail:", fail2ban_menu())


@router.message(BotStates.waiting_f2b_jail_status, F.text)
async def f2b_jail_status_input(message: Message, settings: Settings, state: FSMContext) -> None:
    jail = message.text.strip()
    if not SERVICE_NAME_RE.fullmatch(jail):
        await update_window_from_message(message, "<b>Статус jail</b>\nНекорректное имя. Введите снова:", fail2ban_menu())
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["fail2ban-client", "status", jail], timeout=settings.command_timeout)
    await update_window_from_message(message, command_report(f"fail2ban jail {jail}", result), fail2ban_menu())
    await safe_delete(message)


@router.callback_query(F.data == "f2b:ban")
async def f2b_ban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_f2b_ban)
    await update_window_from_callback(callback, "<b>Ban IP</b>\nВведите: <code>jail ip</code>", fail2ban_menu())


@router.callback_query(F.data == "f2b:unban")
async def f2b_unban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_f2b_unban)
    await update_window_from_callback(callback, "<b>Unban IP</b>\nВведите: <code>jail ip</code>", fail2ban_menu())


@router.message(BotStates.waiting_f2b_ban, F.text)
async def f2b_ban_input(message: Message, settings: Settings, state: FSMContext) -> None:
    parts = message.text.strip().split()
    if len(parts) != 2:
        await update_window_from_message(message, "<b>Ban IP</b>\nФормат: <code>jail ip</code>. Введите снова:", fail2ban_menu())
        await safe_delete(message)
        return
    jail, ip_raw = parts
    if not SERVICE_NAME_RE.fullmatch(jail):
        await update_window_from_message(message, "<b>Ban IP</b>\nНекорректный jail. Введите снова:", fail2ban_menu())
        await safe_delete(message)
        return
    if not parse_ip(ip_raw):
        await update_window_from_message(message, "<b>Ban IP</b>\nНекорректный IP. Введите снова:", fail2ban_menu())
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["fail2ban-client", "set", jail, "banip", ip_raw], timeout=settings.command_timeout)
    await update_window_from_message(message, command_report(f"ban {ip_raw} in {jail}", result), fail2ban_menu())
    await safe_delete(message)


@router.message(BotStates.waiting_f2b_unban, F.text)
async def f2b_unban_input(message: Message, settings: Settings, state: FSMContext) -> None:
    parts = message.text.strip().split()
    if len(parts) != 2:
        await update_window_from_message(message, "<b>Unban IP</b>\nФормат: <code>jail ip</code>. Введите снова:", fail2ban_menu())
        await safe_delete(message)
        return
    jail, ip_raw = parts
    if not SERVICE_NAME_RE.fullmatch(jail):
        await update_window_from_message(message, "<b>Unban IP</b>\nНекорректный jail. Введите снова:", fail2ban_menu())
        await safe_delete(message)
        return
    if not parse_ip(ip_raw):
        await update_window_from_message(message, "<b>Unban IP</b>\nНекорректный IP. Введите снова:", fail2ban_menu())
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["fail2ban-client", "set", jail, "unbanip", ip_raw], timeout=settings.command_timeout)
    await update_window_from_message(message, command_report(f"unban {ip_raw} in {jail}", result), fail2ban_menu())
    await safe_delete(message)
