import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_settings
from app.middleware import AdminMiddleware
from app.routers.fallback import router as fallback_router
from app.routers.files import router as files_router
from app.routers.firewall import router as firewall_router
from app.routers.menu import router as menu_router
from app.routers.network import router as network_router
from app.routers.system import router as system_router
from app.routers.terminal import router as terminal_router
from app.routers.tools_alerts import router as tools_alerts_router
from app.routers.tools_admins import router as tools_admins_router
from app.routers.tools_backup_pro import router as tools_backup_pro_router
from app.routers.tools_docker import router as tools_docker_router
from app.routers.tools_fail2ban import router as tools_fail2ban_router
from app.routers.tools_fw_profiles import router as tools_fw_profiles_router
from app.routers.tools_logs import router as tools_logs_router
from app.routers.tools_main import router as tools_main_router
from app.routers.tools_updates import router as tools_updates_router
from app.runtime import stop_all_metrics
from app.services.alerts import AlertsEngine
from app.services.storage import Storage


def build_dispatcher(admin_middleware: AdminMiddleware) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.message.middleware(admin_middleware)
    dispatcher.callback_query.middleware(admin_middleware)
    dispatcher.include_router(menu_router)
    dispatcher.include_router(network_router)
    dispatcher.include_router(firewall_router)
    dispatcher.include_router(system_router)
    dispatcher.include_router(files_router)
    dispatcher.include_router(tools_main_router)
    dispatcher.include_router(tools_alerts_router)
    dispatcher.include_router(tools_admins_router)
    dispatcher.include_router(tools_fw_profiles_router)
    dispatcher.include_router(tools_logs_router)
    dispatcher.include_router(tools_fail2ban_router)
    dispatcher.include_router(tools_docker_router)
    dispatcher.include_router(tools_updates_router)
    dispatcher.include_router(tools_backup_pro_router)
    dispatcher.include_router(terminal_router)
    dispatcher.include_router(fallback_router)
    return dispatcher


async def main() -> None:
    settings = load_settings()
    storage = Storage()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    middleware = AdminMiddleware(settings.admin_ids, storage)
    dispatcher = build_dispatcher(middleware)
    alert_engine = AlertsEngine(bot, storage, settings.command_timeout)
    alert_task = asyncio.create_task(alert_engine.run())
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot, settings=settings, storage=storage)
    finally:
        alert_task.cancel()
        await asyncio.gather(alert_task, return_exceptions=True)
        await stop_all_metrics()


if __name__ == "__main__":
    asyncio.run(main())
