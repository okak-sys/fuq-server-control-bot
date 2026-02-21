from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.services.storage import Storage


class AdminMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: tuple[int, ...], storage: Storage) -> None:
        self.admin_ids = admin_ids
        self.storage = storage

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user:
            is_allowed = await self.storage.is_admin(user.id, self.admin_ids)
            if not is_allowed:
                if isinstance(event, Message):
                    await event.answer("Доступ запрещен")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Доступ запрещен", show_alert=True)
                return
        chat_id: int | None = None
        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = event.message.chat.id
        if chat_id is not None:
            await self.storage.set_admin_chat_id(chat_id)
        return await handler(event, data)
