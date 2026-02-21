from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.keyboards import admins_menu, fail2ban_menu, firewall_profiles_menu, logs_menu, updates_menu
from app.runtime import stop_metrics, update_window_from_callback
from app.services.storage import Storage
from app.services.updates import detect_package_manager, manager_title
from app.texts import updates_text
from app.views import render_alerts_callback, render_backup_pro_callback, render_docker_callback

router = Router()


@router.callback_query(F.data.startswith("tools:"))
async def tools_router(callback: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await callback.answer()
    if not callback.data:
        return
    await stop_metrics(callback.from_user.id)
    await state.clear()
    if callback.data == "tools:alerts":
        await render_alerts_callback(callback, storage)
    elif callback.data == "tools:fw_profiles":
        await update_window_from_callback(callback, "<b>🧱 Файервол-профили</b>\nВыберите профиль:", firewall_profiles_menu())
    elif callback.data == "tools:logs":
        await update_window_from_callback(callback, "<b>🧾 Журналы</b>\nВыберите источник логов:", logs_menu())
    elif callback.data == "tools:fail2ban":
        await update_window_from_callback(callback, "<b>🔒 Fail2ban</b>\nУправление jail и блокировками:", fail2ban_menu())
    elif callback.data == "tools:docker":
        await render_docker_callback(callback, storage)
    elif callback.data == "tools:updates":
        manager = detect_package_manager()
        await update_window_from_callback(callback, updates_text(manager_title(manager)), updates_menu())
    elif callback.data == "tools:backup_pro":
        await render_backup_pro_callback(callback)
    elif callback.data == "tools:admins":
        await update_window_from_callback(callback, "<b>👤 Админы</b>\nУправление доступом к боту:", admins_menu())
