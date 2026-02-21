import shlex

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common import SERVICE_NAME_RE
from app.config import Settings
from app.keyboards import logs_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.formatting import command_report
from app.services.shell import run_exec, run_shell
from app.states import BotStates

router = Router()


@router.callback_query(F.data == "logs:kernel")
async def logs_kernel(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["journalctl", "-k", "-n", "150", "--no-pager"], timeout=max(settings.command_timeout, 90))
    await update_window_from_callback(callback, command_report("Kernel logs", result), logs_menu())


@router.callback_query(F.data == "logs:auth")
async def logs_auth(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    command = "journalctl -n 500 --no-pager | grep -Ei 'sshd|sudo|authentication|failed password|invalid user' | tail -n 150 || true"
    result = await run_shell(command, timeout=max(settings.command_timeout, 90))
    await update_window_from_callback(callback, command_report("Auth logs", result), logs_menu())


@router.callback_query(F.data == "logs:errors")
async def logs_errors(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["journalctl", "-p", "err", "-n", "150", "--no-pager"], timeout=max(settings.command_timeout, 90))
    await update_window_from_callback(callback, command_report("Error logs", result), logs_menu())


@router.callback_query(F.data == "logs:service")
async def logs_service_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_log_service)
    await update_window_from_callback(callback, "<b>Логи службы</b>\nВведите имя systemd-службы:", logs_menu())


@router.message(BotStates.waiting_log_service, F.text)
async def logs_service_input(message: Message, settings: Settings, state: FSMContext) -> None:
    service = message.text.strip()
    if not SERVICE_NAME_RE.fullmatch(service):
        await update_window_from_message(message, "<b>Логи службы</b>\nНекорректное имя. Введите снова:", logs_menu())
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["journalctl", "-u", service, "-n", "150", "--no-pager"], timeout=max(settings.command_timeout, 90))
    await update_window_from_message(message, command_report(f"journalctl -u {service}", result), logs_menu())
    await safe_delete(message)


@router.callback_query(F.data == "logs:search")
async def logs_search_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_log_search)
    await update_window_from_callback(callback, "<b>Поиск по журналу</b>\nВведите строку поиска:", logs_menu())


@router.message(BotStates.waiting_log_search, F.text)
async def logs_search_input(message: Message, settings: Settings, state: FSMContext) -> None:
    query = message.text.strip()
    if len(query) < 2:
        await update_window_from_message(message, "<b>Поиск</b>\nМинимум 2 символа. Введите снова:", logs_menu())
        await safe_delete(message)
        return
    await state.clear()
    quoted = shlex.quote(query)
    command = f"(journalctl -n 800 --no-pager | grep -i -- {quoted} | tail -n 180) || true"
    result = await run_shell(command, timeout=max(settings.command_timeout, 120))
    await update_window_from_message(message, command_report(f"Поиск: {query}", result), logs_menu())
    await safe_delete(message)
