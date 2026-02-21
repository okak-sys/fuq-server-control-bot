import html


def main_text() -> str:
    return "<b>FUQ Server Control</b>\nЕдиное окно управления Linux-сервером.\nВыберите раздел:"


def menu_text(title: str) -> str:
    return f"<b>{title}</b>\nВыберите действие:"


def tools_text() -> str:
    return "<b>🧰 Инструменты</b>\nРасширенные блоки управления сервером:"


def alerts_text(config: dict) -> str:
    services = ", ".join(config.get("services", [])) if config.get("services") else "не заданы"
    status = "ON" if config.get("enabled") else "OFF"
    return (
        "<b>📈 Мониторинг + алерты</b>\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>CPU порог:</b> {config.get('cpu')}%\n"
        f"<b>RAM порог:</b> {config.get('ram')}%\n"
        f"<b>Disk порог:</b> {config.get('disk')}%\n"
        f"<b>Интервал:</b> {config.get('interval')} c\n"
        f"<b>Cooldown:</b> {config.get('cooldown')} c\n"
        f"<b>Службы:</b> <code>{html.escape(services)}</code>"
    )


def docker_text(compose_file: str) -> str:
    shown = compose_file if compose_file else "не задан"
    return f"<b>🐳 Docker/Compose</b>\n<b>Compose file:</b> <code>{html.escape(shown)}</code>"


def updates_text(manager_title: str) -> str:
    return (
        "<b>⬆️ Управление обновлениями</b>\n"
        f"<b>Менеджер пакетов:</b> {manager_title}\n"
        "Проверка, upgrade и очистка кэша."
    )


def backup_pro_text() -> str:
    return (
        "<b>💾 Бэкапы PRO</b>\n"
        "Архивирование, список, скачивание, восстановление и удаление.\n"
        "Рабочая директория архивов: <code>/backup</code>"
    )
