import html
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common import SERVICE_NAME_RE, parse_interval, parse_percent
from app.keyboards import alerts_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.storage import Storage
from app.states import BotStates
from app.texts import alerts_text
from app.views import render_alerts_callback, render_alerts_message

router = Router()


@router.callback_query(F.data == "al:toggle")
async def alerts_toggle(callback: CallbackQuery, storage: Storage) -> None:
    await callback.answer()
    config = await storage.get_alerts()
    updated = await storage.set_alert_value("enabled", not bool(config.get("enabled")))
    await update_window_from_callback(callback, alerts_text(updated), alerts_menu(bool(updated.get("enabled"))))


@router.callback_query(F.data == "al:set_cpu")
async def alerts_set_cpu_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_alert_cpu)
    await update_window_from_callback(callback, "<b>CPU порог</b>\nВведите значение 1-100:", alerts_menu(True))


@router.callback_query(F.data == "al:set_ram")
async def alerts_set_ram_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_alert_ram)
    await update_window_from_callback(callback, "<b>RAM порог</b>\nВведите значение 1-100:", alerts_menu(True))


@router.callback_query(F.data == "al:set_disk")
async def alerts_set_disk_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_alert_disk)
    await update_window_from_callback(callback, "<b>Disk порог</b>\nВведите значение 1-100:", alerts_menu(True))


@router.callback_query(F.data == "al:set_interval")
async def alerts_set_interval_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_alert_interval)
    await update_window_from_callback(callback, "<b>Интервал проверки</b>\nВведите секунды 10-3600:", alerts_menu(True))


@router.callback_query(F.data == "al:set_cooldown")
async def alerts_set_cooldown_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_alert_cooldown)
    await update_window_from_callback(callback, "<b>Cooldown</b>\nВведите секунды 30-86400:", alerts_menu(True))


@router.callback_query(F.data == "al:set_services")
async def alerts_set_services_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_alert_services)
    text = (
        "<b>Службы для контроля</b>\n"
        "Введите имена через запятую.\n"
        "Пример: <code>ssh, nginx, docker</code>\n"
        "Для очистки: <code>none</code>"
    )
    await update_window_from_callback(callback, text, alerts_menu(True))


@router.callback_query(F.data == "al:test")
async def alerts_test(callback: CallbackQuery, storage: Storage) -> None:
    await callback.answer("Тест отправлен")
    chat_id = await storage.get_admin_chat_id()
    if chat_id:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await callback.bot.send_message(chat_id, f"🧪 Тест алерта\nВремя: <code>{now}</code>")
    await render_alerts_callback(callback, storage)


@router.message(BotStates.waiting_alert_cpu, F.text)
async def alerts_set_cpu_input(message: Message, storage: Storage, state: FSMContext) -> None:
    value = parse_percent(message.text.strip())
    if value is None:
        await update_window_from_message(message, "<b>CPU порог</b>\nНужно число 1-100. Введите снова:", alerts_menu(True))
        await safe_delete(message)
        return
    await storage.set_alert_value("cpu", value)
    await state.clear()
    await render_alerts_message(message, storage)
    await safe_delete(message)


@router.message(BotStates.waiting_alert_ram, F.text)
async def alerts_set_ram_input(message: Message, storage: Storage, state: FSMContext) -> None:
    value = parse_percent(message.text.strip())
    if value is None:
        await update_window_from_message(message, "<b>RAM порог</b>\nНужно число 1-100. Введите снова:", alerts_menu(True))
        await safe_delete(message)
        return
    await storage.set_alert_value("ram", value)
    await state.clear()
    await render_alerts_message(message, storage)
    await safe_delete(message)


@router.message(BotStates.waiting_alert_disk, F.text)
async def alerts_set_disk_input(message: Message, storage: Storage, state: FSMContext) -> None:
    value = parse_percent(message.text.strip())
    if value is None:
        await update_window_from_message(message, "<b>Disk порог</b>\nНужно число 1-100. Введите снова:", alerts_menu(True))
        await safe_delete(message)
        return
    await storage.set_alert_value("disk", value)
    await state.clear()
    await render_alerts_message(message, storage)
    await safe_delete(message)


@router.message(BotStates.waiting_alert_interval, F.text)
async def alerts_set_interval_input(message: Message, storage: Storage, state: FSMContext) -> None:
    value = parse_interval(message.text.strip(), 10, 3600)
    if value is None:
        await update_window_from_message(message, "<b>Интервал</b>\nНужно число 10-3600. Введите снова:", alerts_menu(True))
        await safe_delete(message)
        return
    await storage.set_alert_value("interval", value)
    await state.clear()
    await render_alerts_message(message, storage)
    await safe_delete(message)


@router.message(BotStates.waiting_alert_cooldown, F.text)
async def alerts_set_cooldown_input(message: Message, storage: Storage, state: FSMContext) -> None:
    value = parse_interval(message.text.strip(), 30, 86400)
    if value is None:
        await update_window_from_message(message, "<b>Cooldown</b>\nНужно число 30-86400. Введите снова:", alerts_menu(True))
        await safe_delete(message)
        return
    await storage.set_alert_value("cooldown", value)
    await state.clear()
    await render_alerts_message(message, storage)
    await safe_delete(message)


@router.message(BotStates.waiting_alert_services, F.text)
async def alerts_set_services_input(message: Message, storage: Storage, state: FSMContext) -> None:
    raw = message.text.strip()
    if raw.lower() in {"none", "clear", "-", "нет"}:
        await storage.set_alert_services([])
        await state.clear()
        await render_alerts_message(message, storage)
        await safe_delete(message)
        return
    names = [part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()]
    if not names:
        await update_window_from_message(message, "<b>Службы</b>\nВведите имена или <code>none</code>:", alerts_menu(True))
        await safe_delete(message)
        return
    invalid = [name for name in names if not SERVICE_NAME_RE.fullmatch(name)]
    if invalid:
        await update_window_from_message(
            message,
            f"<b>Службы</b>\nНекорректные имена: <code>{html.escape(', '.join(invalid))}</code>",
            alerts_menu(True),
        )
        await safe_delete(message)
        return
    await storage.set_alert_services(names)
    await state.clear()
    await render_alerts_message(message, storage)
    await safe_delete(message)
