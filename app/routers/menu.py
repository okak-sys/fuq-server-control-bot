from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import backups_menu, files_menu, firewall_menu, main_menu, network_menu, system_menu, terminal_menu, tools_menu
from app.runtime import safe_delete, stop_metrics, update_window_from_callback, update_window_from_message
from app.texts import main_text, menu_text, tools_text
from app.states import BotStates

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await stop_metrics(message.from_user.id)
    await state.clear()
    await update_window_from_message(message, main_text(), main_menu())
    await safe_delete(message)


@router.callback_query(F.data.startswith("menu:"))
async def menu_router(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data:
        return
    user_id = callback.from_user.id
    await stop_metrics(user_id)
    if callback.data == "menu:terminal":
        await state.set_state(BotStates.terminal_mode)
        text = (
            "<b>Терминал</b>\n"
            "Режим включен. Отправляйте Bash-команды обычными сообщениями.\n"
            "Ответ консоли приходит новым сообщением."
        )
        await update_window_from_callback(callback, text, terminal_menu())
        return
    await state.clear()
    if callback.data == "menu:main":
        await update_window_from_callback(callback, main_text(), main_menu())
    elif callback.data == "menu:network":
        await update_window_from_callback(callback, menu_text("🌐 СЕТЬ"), network_menu())
    elif callback.data == "menu:firewall":
        await update_window_from_callback(callback, menu_text("🛡️ ФАЙЕРВОЛ"), firewall_menu())
    elif callback.data == "menu:system":
        await update_window_from_callback(callback, menu_text("⚙️ СИСТЕМА"), system_menu())
    elif callback.data == "menu:files":
        await update_window_from_callback(callback, menu_text("📂 ФАЙЛЫ"), files_menu())
    elif callback.data == "menu:backups":
        await update_window_from_callback(callback, menu_text("📦 БЭКАПЫ"), backups_menu())
    elif callback.data == "menu:tools":
        await update_window_from_callback(callback, tools_text(), tools_menu())
