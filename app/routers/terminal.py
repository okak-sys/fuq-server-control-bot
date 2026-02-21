from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.keyboards import main_menu
from app.runtime import update_window_from_callback
from app.services.formatting import command_report
from app.services.shell import run_shell
from app.states import BotStates
from app.texts import main_text

router = Router()


@router.callback_query(F.data == "term:exit")
async def terminal_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await update_window_from_callback(callback, main_text(), main_menu())


@router.message(BotStates.terminal_mode, F.text)
async def terminal_exec(message: Message, settings: Settings, state: FSMContext) -> None:
    current = await state.get_state()
    if current != BotStates.terminal_mode.state:
        return
    command = message.text.strip()
    if not command:
        return
    result = await run_shell(command, timeout=settings.terminal_timeout)
    await message.answer(command_report("Терминал", result, limit=2800))
