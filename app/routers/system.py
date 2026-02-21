import asyncio
import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common import SERVICE_NAME_RE, parse_pid
from app.config import Settings
from app.keyboards import metrics_menu, service_actions_menu, service_input_menu, system_menu
from app.runtime import RUNTIME, metrics_loop, safe_delete, stop_metrics, update_window_from_callback, update_window_from_message
from app.services.formatting import command_report, pre
from app.services.metrics import system_metrics_text
from app.services.shell import run_exec, run_shell
from app.states import BotStates
from app.texts import menu_text

router = Router()


@router.callback_query(F.data == "sys:metrics")
async def sys_metrics(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    user_id = callback.from_user.id
    await stop_metrics(user_id)
    await update_window_from_callback(callback, system_metrics_text(), metrics_menu())
    if callback.message:
        task = asyncio.create_task(metrics_loop(callback.bot, callback.message.chat.id, callback.message.message_id, metrics_menu()))
        RUNTIME.metrics_tasks[user_id] = task


@router.callback_query(F.data == "sys:metrics:stop")
async def sys_metrics_stop(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Обновление остановлено")
    await stop_metrics(callback.from_user.id)
    await state.clear()
    await update_window_from_callback(callback, menu_text("⚙️ СИСТЕМА"), system_menu())


@router.callback_query(F.data == "sys:procs")
async def sys_processes(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await stop_metrics(callback.from_user.id)
    await state.clear()
    result = await run_shell("ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 16", timeout=settings.command_timeout)
    await update_window_from_callback(callback, command_report("ТОП-15 процессов", result), system_menu())


@router.callback_query(F.data == "sys:kill")
async def sys_kill_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await stop_metrics(callback.from_user.id)
    await state.set_state(BotStates.waiting_kill_pid)
    await update_window_from_callback(callback, "<b>Kill PID</b>\nВведите PID процесса:", system_menu())


@router.message(BotStates.waiting_kill_pid, F.text)
async def sys_kill_input(message: Message, settings: Settings, state: FSMContext) -> None:
    pid = parse_pid(message.text.strip())
    if pid is None:
        await update_window_from_message(message, "<b>Kill PID</b>\nНужно положительное число. Введите снова:", system_menu())
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["kill", "-9", str(pid)], timeout=settings.command_timeout)
    await update_window_from_message(message, command_report(f"Kill PID {pid}", result), system_menu())
    await safe_delete(message)


@router.callback_query(F.data == "sys:services")
async def sys_service_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await stop_metrics(callback.from_user.id)
    await state.set_state(BotStates.waiting_service_name)
    await update_window_from_callback(callback, "<b>Службы</b>\nВведите имя службы systemd:", service_input_menu())


@router.message(BotStates.waiting_service_name, F.text)
async def sys_service_input(message: Message, state: FSMContext) -> None:
    service_name = message.text.strip()
    if not SERVICE_NAME_RE.fullmatch(service_name):
        await update_window_from_message(message, "<b>Службы</b>\nНекорректное имя. Введите снова:", service_input_menu())
        await safe_delete(message)
        return
    await state.update_data(service_name=service_name)
    await state.set_state(BotStates.service_selected)
    await update_window_from_message(
        message,
        f"<b>Служба выбрана:</b> <code>{html.escape(service_name)}</code>\nВыберите действие:",
        service_actions_menu(),
    )
    await safe_delete(message)


@router.callback_query(F.data.in_({"svc:start", "svc:stop", "svc:restart"}))
async def sys_service_action(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    service_name = data.get("service_name")
    if not service_name:
        await state.set_state(BotStates.waiting_service_name)
        await update_window_from_callback(callback, "<b>Службы</b>\nСначала введите имя службы:", service_input_menu())
        return
    action = callback.data.split(":", 1)[1]
    action_result = await run_exec(["systemctl", action, service_name], timeout=settings.command_timeout)
    status_result = await run_exec(["systemctl", "is-active", service_name], timeout=settings.command_timeout)
    status_text = status_result.stdout.strip() or status_result.stderr.strip() or "(пусто)"
    text = (
        f"<b>Служба:</b> <code>{html.escape(service_name)}</code>\n"
        f"{command_report(f'systemctl {action}', action_result, limit=1500)}\n"
        f"<b>Текущее состояние:</b>\n{pre(status_text, limit=300)}"
    )
    await state.set_state(BotStates.service_selected)
    await update_window_from_callback(callback, text, service_actions_menu())
