from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common import CONTAINER_NAME_RE, resolve_compose_file
from app.config import Settings
from app.keyboards import docker_menu
from app.runtime import safe_delete, update_window_from_callback, update_window_from_message
from app.services.formatting import command_report
from app.services.shell import run_exec, run_shell
from app.services.storage import Storage
from app.states import BotStates
from app.views import render_docker_message

router = Router()


@router.callback_query(F.data == "dock:info")
async def docker_info(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    result = await run_exec(["docker", "info"], timeout=max(settings.command_timeout, 90))
    await update_window_from_callback(callback, command_report("docker info", result), docker_menu())


@router.callback_query(F.data == "dock:containers")
async def docker_containers(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    command = "docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'"
    result = await run_shell(command, timeout=max(settings.command_timeout, 90))
    await update_window_from_callback(callback, command_report("Контейнеры", result), docker_menu())


@router.callback_query(F.data == "dock:images")
async def docker_images(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    command = "docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.ID}}\\t{{.Size}}'"
    result = await run_shell(command, timeout=max(settings.command_timeout, 90))
    await update_window_from_callback(callback, command_report("Docker образы", result), docker_menu())


@router.callback_query(F.data == "dock:set_compose")
async def docker_set_compose_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_docker_compose_path)
    text = (
        "<b>Compose path</b>\n"
        "Введите абсолютный путь к папке проекта или к compose-файлу.\n"
        "Ищутся: <code>docker-compose.yml</code>, <code>compose.yml</code>, <code>compose.yaml</code>"
    )
    await update_window_from_callback(callback, text, docker_menu())


@router.message(BotStates.waiting_docker_compose_path, F.text)
async def docker_set_compose_input(message: Message, storage: Storage, state: FSMContext) -> None:
    compose_file = resolve_compose_file(message.text.strip())
    if not compose_file:
        await update_window_from_message(
            message,
            "<b>Compose path</b>\nНе найден compose-файл по этому пути. Введите снова:",
            docker_menu(),
        )
        await safe_delete(message)
        return
    await storage.set_compose_project(str(compose_file))
    await state.clear()
    await render_docker_message(message, storage)
    await safe_delete(message)


@router.callback_query(F.data.in_({"dock:compose_ps", "dock:compose_up", "dock:compose_down", "dock:compose_pull"}))
async def docker_compose_action(callback: CallbackQuery, settings: Settings, storage: Storage, state: FSMContext) -> None:
    await callback.answer("Выполняю...")
    await state.clear()
    compose_file = await storage.get_compose_project()
    if not compose_file:
        await update_window_from_callback(callback, "<b>Compose path не задан</b>\nСначала выберите Set Compose Path.", docker_menu())
        return
    compose_path = resolve_compose_file(compose_file)
    if not compose_path:
        await update_window_from_callback(callback, "<b>Compose file не найден</b>", docker_menu())
        return
    if callback.data == "dock:compose_ps":
        command = ["docker", "compose", "-f", str(compose_path), "ps"]
        title = "docker compose ps"
        timeout = max(settings.command_timeout, 90)
    elif callback.data == "dock:compose_up":
        command = ["docker", "compose", "-f", str(compose_path), "up", "-d"]
        title = "docker compose up -d"
        timeout = max(settings.command_timeout, 600)
    elif callback.data == "dock:compose_down":
        command = ["docker", "compose", "-f", str(compose_path), "down"]
        title = "docker compose down"
        timeout = max(settings.command_timeout, 300)
    else:
        command = ["docker", "compose", "-f", str(compose_path), "pull"]
        title = "docker compose pull"
        timeout = max(settings.command_timeout, 1200)
    result = await run_exec(command, timeout=timeout)
    await update_window_from_callback(callback, command_report(title, result), docker_menu())


@router.callback_query(F.data == "dock:logs")
async def docker_logs_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_docker_logs_container)
    await update_window_from_callback(callback, "<b>Логи контейнера</b>\nВведите имя контейнера:", docker_menu())


@router.message(BotStates.waiting_docker_logs_container, F.text)
async def docker_logs_input(message: Message, settings: Settings, state: FSMContext) -> None:
    container = message.text.strip()
    if not CONTAINER_NAME_RE.fullmatch(container):
        await update_window_from_message(message, "<b>Логи контейнера</b>\nНекорректное имя. Введите снова:", docker_menu())
        await safe_delete(message)
        return
    await state.clear()
    result = await run_exec(["docker", "logs", "--tail", "120", container], timeout=max(settings.command_timeout, 120))
    await update_window_from_message(message, command_report(f"docker logs {container}", result), docker_menu())
    await safe_delete(message)
