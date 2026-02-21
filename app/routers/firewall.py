import asyncio
import ipaddress

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common import compact_report, disable_firewall, parse_port, parse_ports_csv, apply_firewall_safe_mode
from app.config import Settings
from app.keyboards import firewall_confirm_menu, firewall_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.formatting import command_report
from app.services.shell import run_exec
from app.services.storage import Storage
from app.states import BotStates

router = Router()


@router.callback_query(F.data == "fw:rules")
async def fw_rules(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["iptables", "-L", "-n", "-v", "--line-numbers"], timeout=settings.command_timeout)
    await update_window_from_callback(callback, command_report("Текущие правила iptables", result), firewall_menu())


@router.callback_query(F.data == "fw:enable")
async def fw_enable(callback: CallbackQuery, settings: Settings, storage: Storage, state: FSMContext) -> None:
    await callback.answer("Применяю правила...")
    await state.clear()
    safe_ports = await storage.get_firewall_ports(settings.firewall_safe_ports)
    text = await apply_firewall_safe_mode(safe_ports, timeout=settings.command_timeout)
    await storage.set_firewall_enabled(True)
    await update_window_from_callback(callback, text, firewall_menu())


@router.callback_query(F.data == "fw:disable")
async def fw_disable(callback: CallbackQuery, settings: Settings, storage: Storage, state: FSMContext) -> None:
    await callback.answer("Отключаю...")
    await state.clear()
    text = await disable_firewall(timeout=settings.command_timeout)
    await storage.set_firewall_enabled(False)
    await update_window_from_callback(callback, text, firewall_menu())


@router.callback_query(F.data == "fw:safe_ports")
async def fw_safe_ports_prompt(callback: CallbackQuery, settings: Settings, storage: Storage, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_fw_safe_ports)
    ports = await storage.get_firewall_ports(settings.firewall_safe_ports)
    current = ", ".join(str(item) for item in ports)
    text = (
        "<b>Безопасные порты</b>\n"
        f"Текущие: <code>{current}</code>\n"
        "Введите список через запятую, пример: <code>22,80,443</code>"
    )
    await update_window_from_callback(callback, text, firewall_menu())


@router.callback_query(F.data == "fw:open")
async def fw_open_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_open_port)
    await update_window_from_callback(callback, "<b>Открыть порт</b>\nВведите номер порта (1-65535):", firewall_menu())


@router.callback_query(F.data == "fw:close")
async def fw_close_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_close_port)
    await update_window_from_callback(callback, "<b>Закрыть порт</b>\nВведите номер порта (1-65535):", firewall_menu())


@router.callback_query(F.data == "fw:ban")
async def fw_ban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_ban_ip)
    await update_window_from_callback(callback, "<b>Бан IP</b>\nВведите IP-адрес для блокировки:", firewall_menu())


@router.callback_query(F.data == "fw:flush")
async def fw_flush_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await update_window_from_callback(
        callback,
        "<b>Сброс iptables</b>\nПодтвердите полный сброс правил:",
        firewall_confirm_menu(),
    )


@router.callback_query(F.data == "fw:flush:no")
async def fw_flush_cancel(callback: CallbackQuery) -> None:
    await callback.answer()
    await update_window_from_callback(callback, "<b>Сброс отменен</b>", firewall_menu())


@router.callback_query(F.data == "fw:flush:yes")
async def fw_flush_confirm(callback: CallbackQuery, settings: Settings, storage: Storage, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["iptables", "-F"], timeout=settings.command_timeout)
    await storage.set_firewall_enabled(False)
    await update_window_from_callback(callback, command_report("Сброс iptables", result), firewall_menu())


@router.message(BotStates.waiting_fw_safe_ports, F.text)
async def fw_safe_ports_input(message: Message, settings: Settings, storage: Storage, state: FSMContext) -> None:
    ports = parse_ports_csv(message.text.strip())
    if not ports:
        await update_window_from_message(
            message,
            "<b>Безопасные порты</b>\nНужен список чисел 1-65535 через запятую. Введите снова:",
            firewall_menu(),
        )
        await safe_delete(message)
        return
    await storage.set_firewall_ports(ports)
    await state.clear()
    text = (
        "<b>Безопасные порты сохранены</b>\n"
        f"<code>{', '.join(str(item) for item in ports)}</code>\n"
        "Нажмите ВКЛЮЧИТЬ для применения фаервола."
    )
    await update_window_from_message(message, text, firewall_menu())
    await safe_delete(message)


@router.message(BotStates.waiting_open_port, F.text)
async def fw_open_input(message: Message, settings: Settings, state: FSMContext) -> None:
    port = parse_port(message.text.strip())
    if port is None:
        await update_window_from_message(message, "<b>Открыть порт</b>\nНужно число 1-65535. Введите снова:", firewall_menu())
        await safe_delete(message)
        return
    await state.clear()
    tcp_task = run_exec(["iptables", "-I", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], timeout=settings.command_timeout)
    udp_task = run_exec(["iptables", "-I", "INPUT", "-p", "udp", "--dport", str(port), "-j", "ACCEPT"], timeout=settings.command_timeout)
    tcp, udp = await asyncio.gather(tcp_task, udp_task)
    await update_window_from_message(message, compact_report(f"Порт {port} открыт", [("TCP", tcp), ("UDP", udp)]), firewall_menu())
    await safe_delete(message)


@router.message(BotStates.waiting_close_port, F.text)
async def fw_close_input(message: Message, settings: Settings, state: FSMContext) -> None:
    port = parse_port(message.text.strip())
    if port is None:
        await update_window_from_message(message, "<b>Закрыть порт</b>\nНужно число 1-65535. Введите снова:", firewall_menu())
        await safe_delete(message)
        return
    await state.clear()
    tcp_task = run_exec(["iptables", "-D", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], timeout=settings.command_timeout)
    udp_task = run_exec(["iptables", "-D", "INPUT", "-p", "udp", "--dport", str(port), "-j", "ACCEPT"], timeout=settings.command_timeout)
    tcp, udp = await asyncio.gather(tcp_task, udp_task)
    await update_window_from_message(message, compact_report(f"Порт {port} закрыт", [("TCP", tcp), ("UDP", udp)]), firewall_menu())
    await safe_delete(message)


@router.message(BotStates.waiting_ban_ip, F.text)
async def fw_ban_input(message: Message, settings: Settings, state: FSMContext) -> None:
    ip_raw = message.text.strip()
    try:
        ipaddress.ip_address(ip_raw)
    except ValueError:
        await update_window_from_message(message, "<b>Бан IP</b>\nНеверный IP. Введите снова:", firewall_menu())
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["iptables", "-I", "INPUT", "-s", ip_raw, "-j", "DROP"], timeout=settings.command_timeout)
    await update_window_from_message(message, command_report(f"IP {ip_raw} заблокирован", result), firewall_menu())
    await safe_delete(message)
