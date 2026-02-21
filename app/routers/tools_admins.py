from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.keyboards import admins_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.storage import Storage
from app.states import BotStates

router = Router()


def _format_admins(admin_ids: list[int]) -> str:
    if not admin_ids:
        return "<b>Админы</b>\n(пусто)"
    lines = [str(item) for item in admin_ids]
    return "<b>Админы</b>\n<pre>" + "\n".join(lines) + "</pre>"


@router.callback_query(F.data == "adm:list")
async def admins_list(callback: CallbackQuery, storage: Storage, settings: Settings) -> None:
    await callback.answer()
    admin_ids = await storage.list_admin_ids(settings.admin_ids)
    await update_window_from_callback(callback, _format_admins(admin_ids), admins_menu())


@router.callback_query(F.data == "adm:add")
async def admins_add_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_add_admin_id)
    await update_window_from_callback(
        callback,
        "<b>Добавить админа</b>\nВведите Telegram user id:",
        admins_menu(),
    )


@router.callback_query(F.data == "adm:remove")
async def admins_remove_prompt(callback: CallbackQuery, state: FSMContext, storage: Storage, settings: Settings) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_remove_admin_id)
    admin_ids = await storage.list_admin_ids(settings.admin_ids)
    text = _format_admins(admin_ids) + "\n<b>Введите id для удаления:</b>"
    await update_window_from_callback(callback, text, admins_menu())


@router.message(BotStates.waiting_add_admin_id, F.text)
async def admins_add_input(message: Message, state: FSMContext, storage: Storage, settings: Settings) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await update_window_from_message(message, "<b>Добавить админа</b>\nНужен числовой user id. Введите снова:", admins_menu())
        await safe_delete(message)
        return
    admin_id = int(raw)
    await storage.add_admin_id(admin_id)
    await state.clear()
    admin_ids = await storage.list_admin_ids(settings.admin_ids)
    await update_window_from_message(message, _format_admins(admin_ids), admins_menu())
    await safe_delete(message)


@router.message(BotStates.waiting_remove_admin_id, F.text)
async def admins_remove_input(message: Message, state: FSMContext, storage: Storage, settings: Settings) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await update_window_from_message(message, "<b>Удалить админа</b>\nНужен числовой user id. Введите снова:", admins_menu())
        await safe_delete(message)
        return
    admin_id = int(raw)
    if admin_id in settings.admin_ids:
        await update_window_from_message(
            message,
            "<b>Удалить админа</b>\nЭтот id указан как основной в .env и не может быть удален из бота.",
            admins_menu(),
        )
        await safe_delete(message)
        return
    await storage.remove_admin_id(admin_id)
    await state.clear()
    admin_ids = await storage.list_admin_ids(settings.admin_ids)
    await update_window_from_message(message, _format_admins(admin_ids), admins_menu())
    await safe_delete(message)
