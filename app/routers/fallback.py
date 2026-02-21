from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import main_menu
from app.runtime import safe_delete, update_window_from_message
from app.texts import main_text

router = Router()


@router.message(F.text)
async def fallback_text(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current:
        return
    await update_window_from_message(message, main_text(), main_menu())
    await safe_delete(message)
