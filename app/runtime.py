import asyncio
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from app.services.metrics import system_metrics_text


@dataclass(slots=True)
class RuntimeState:
    windows: dict[int, tuple[int, int]] = field(default_factory=dict)
    metrics_tasks: dict[int, asyncio.Task] = field(default_factory=dict)


RUNTIME = RuntimeState()


async def safe_delete(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        return


def remember_window(user_id: int, chat_id: int, message_id: int) -> None:
    RUNTIME.windows[user_id] = (chat_id, message_id)


async def update_window_from_callback(callback: CallbackQuery, text: str, reply_markup) -> None:
    if not callback.message:
        return
    remember_window(callback.from_user.id, callback.message.chat.id, callback.message.message_id)
    try:
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        sent = await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=reply_markup,
        )
        remember_window(callback.from_user.id, sent.chat.id, sent.message_id)


async def update_window_from_message(message: Message, text: str, reply_markup) -> None:
    user_id = message.from_user.id
    entry = RUNTIME.windows.get(user_id)
    if entry and entry[0] == message.chat.id:
        try:
            await message.bot.edit_message_text(
                chat_id=entry[0],
                message_id=entry[1],
                text=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest:
            pass
    sent = await message.answer(text=text, reply_markup=reply_markup)
    remember_window(user_id, sent.chat.id, sent.message_id)


async def stop_metrics(user_id: int) -> None:
    task = RUNTIME.metrics_tasks.pop(user_id, None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def stop_all_metrics() -> None:
    tasks = list(RUNTIME.metrics_tasks.values())
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    RUNTIME.metrics_tasks.clear()


async def metrics_loop(bot: Bot, chat_id: int, message_id: int, reply_markup) -> None:
    while True:
        text = system_metrics_text()
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                return
        await asyncio.sleep(2)
