from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common import apply_firewall_profile, parse_ip
from app.config import Settings
from app.keyboards import firewall_profile_confirm_menu, firewall_profiles_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.formatting import command_report
from app.services.shell import run_exec
from app.states import BotStates

router = Router()


@router.callback_query(F.data == "fwp:show")
async def firewall_profile_show(callback: CallbackQuery, settings: Settings) -> None:
    await callback.answer()
    result = await run_exec(["iptables", "-L", "-n", "-v", "--line-numbers"], timeout=settings.command_timeout)
    await update_window_from_callback(callback, command_report("Текущие правила iptables", result), firewall_profiles_menu())


@router.callback_query(F.data.startswith("fwp:ask:"))
async def firewall_profile_ask(callback: CallbackQuery) -> None:
    await callback.answer()
    profile = callback.data.split(":")[-1]
    profile_map = {
        "web": "Открывает 22/80/443 и закрывает остальное.",
        "ssh": "Оставляет только SSH 22 и системные исключения.",
        "db": "Открывает 22/80/443 и жестко закрывает популярные DB-порты.",
    }
    if profile not in profile_map:
        await update_window_from_callback(callback, "<b>Неизвестный профиль</b>", firewall_profiles_menu())
        return
    text = f"<b>Профиль {profile.upper()}</b>\n{profile_map[profile]}\nПодтвердите применение."
    await update_window_from_callback(callback, text, firewall_profile_confirm_menu(profile))


@router.callback_query(F.data.startswith("fwp:apply:"))
async def firewall_profile_apply(callback: CallbackQuery, settings: Settings) -> None:
    await callback.answer()
    profile = callback.data.split(":")[-1]
    if profile not in {"web", "ssh", "db"}:
        await update_window_from_callback(callback, "<b>Неизвестный профиль</b>", firewall_profiles_menu())
        return
    text = await apply_firewall_profile(profile, timeout=settings.command_timeout)
    await update_window_from_callback(callback, text, firewall_profiles_menu())


@router.callback_query(F.data == "fwp:panic")
async def firewall_profile_panic_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_firewall_panic_ip)
    await update_window_from_callback(
        callback,
        "<b>Panic профиль</b>\nВведите ваш внешний IP для сохранения SSH-доступа:",
        firewall_profiles_menu(),
    )


@router.message(BotStates.waiting_firewall_panic_ip, F.text)
async def firewall_profile_panic_input(message: Message, settings: Settings, state: FSMContext) -> None:
    ip_raw = parse_ip(message.text.strip())
    if not ip_raw:
        await update_window_from_message(message, "<b>Panic профиль</b>\nНеверный IP. Введите снова:", firewall_profiles_menu())
        await safe_delete(message)
        return
    await state.clear()
    text = await apply_firewall_profile("panic", timeout=settings.command_timeout, admin_ip=ip_raw)
    await update_window_from_message(message, text, firewall_profiles_menu())
    await safe_delete(message)
