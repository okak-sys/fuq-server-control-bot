import ipaddress
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.keyboards import network_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.formatting import command_report
from app.services.shell import run_exec
from app.states import BotStates

router = Router()

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)([A-Za-z0-9-]{1,63})(\.(?!-)[A-Za-z0-9-]{1,63})*(?<!-)$"
)


def is_ping_target_valid(target: str) -> bool:
    if not target or len(target) > 253:
        return False
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        pass
    if target.lower() == "localhost":
        return True
    return bool(DOMAIN_RE.fullmatch(target))


@router.callback_query(F.data == "net:ports")
async def net_ports(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["ss", "-tulpnH"], timeout=settings.command_timeout)
    await update_window_from_callback(callback, command_report("Список портов", result), network_menu())


@router.callback_query(F.data == "net:ifaces")
async def net_ifaces(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["ip", "-br", "a"], timeout=settings.command_timeout)
    await update_window_from_callback(callback, command_report("Сетевые интерфейсы", result), network_menu())


@router.callback_query(F.data == "net:ping")
async def net_ping_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_ping)
    await update_window_from_callback(callback, "<b>Пинг</b>\nВведите IP или домен:", network_menu())


@router.message(BotStates.waiting_ping, F.text)
async def net_ping_input(message: Message, settings: Settings, state: FSMContext) -> None:
    target = message.text.strip()
    if not is_ping_target_valid(target):
        await update_window_from_message(
            message,
            "<b>Пинг</b>\nНеверный формат. Введите корректный IP или домен:",
            network_menu(),
        )
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["ping", "-c", "4", "-W", "2", target], timeout=max(settings.command_timeout, 20))
    await update_window_from_message(message, command_report(f"Пинг {target}", result), network_menu())
    await safe_delete(message)
