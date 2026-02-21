from aiogram.types import CallbackQuery, Message

from app.keyboards import alerts_menu, backup_pro_menu, docker_menu
from app.runtime import update_window_from_callback, update_window_from_message
from app.services.storage import Storage
from app.texts import alerts_text, backup_pro_text, docker_text


async def render_alerts_callback(callback: CallbackQuery, storage: Storage) -> None:
    config = await storage.get_alerts()
    await update_window_from_callback(callback, alerts_text(config), alerts_menu(bool(config.get("enabled"))))


async def render_alerts_message(message: Message, storage: Storage) -> None:
    config = await storage.get_alerts()
    await update_window_from_message(message, alerts_text(config), alerts_menu(bool(config.get("enabled"))))


async def render_docker_callback(callback: CallbackQuery, storage: Storage) -> None:
    compose_file = await storage.get_compose_project()
    await update_window_from_callback(callback, docker_text(compose_file), docker_menu())


async def render_docker_message(message: Message, storage: Storage) -> None:
    compose_file = await storage.get_compose_project()
    await update_window_from_message(message, docker_text(compose_file), docker_menu())


async def render_backup_pro_callback(callback: CallbackQuery) -> None:
    await update_window_from_callback(callback, backup_pro_text(), backup_pro_menu())
