from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 СЕТЬ", callback_data="menu:network")
    kb.button(text="🛡️ ФАЙЕРВОЛ", callback_data="menu:firewall")
    kb.button(text="⚙️ СИСТЕМА", callback_data="menu:system")
    kb.button(text="📂 ФАЙЛЫ", callback_data="menu:files")
    kb.button(text="📦 БЭКАПЫ", callback_data="menu:backups")
    kb.button(text="🐚 ТЕРМИНАЛ", callback_data="menu:terminal")
    kb.button(text="🧰 ИНСТРУМЕНТЫ", callback_data="menu:tools")
    kb.adjust(3, 3, 1)
    return kb.as_markup()


def network_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Список портов", callback_data="net:ports")
    kb.button(text="Интерфейсы", callback_data="net:ifaces")
    kb.button(text="Пинг", callback_data="net:ping")
    kb.button(text="⬅️ В главное", callback_data="menu:main")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def firewall_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Текущие правила", callback_data="fw:rules")
    kb.button(text="ВКЛЮЧИТЬ", callback_data="fw:enable")
    kb.button(text="ВЫКЛЮЧИТЬ", callback_data="fw:disable")
    kb.button(text="Безопасные порты", callback_data="fw:safe_ports")
    kb.button(text="ОТКРЫТЬ ПОРТ", callback_data="fw:open")
    kb.button(text="ЗАКРЫТЬ ПОРТ", callback_data="fw:close")
    kb.button(text="ЗАБАНИТЬ IP", callback_data="fw:ban")
    kb.button(text="СБРОС", callback_data="fw:flush")
    kb.button(text="⬅️ В главное", callback_data="menu:main")
    kb.adjust(1, 2, 1, 2, 1, 1)
    return kb.as_markup()


def firewall_confirm_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="fw:flush:yes")
    kb.button(text="❌ Отмена", callback_data="fw:flush:no")
    kb.adjust(2)
    return kb.as_markup()


def system_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Метрики", callback_data="sys:metrics")
    kb.button(text="Процессы", callback_data="sys:procs")
    kb.button(text="Kill PID", callback_data="sys:kill")
    kb.button(text="Службы", callback_data="sys:services")
    kb.button(text="⬅️ В главное", callback_data="menu:main")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def metrics_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Остановить", callback_data="sys:metrics:stop")
    kb.button(text="⬅️ Система", callback_data="menu:system")
    kb.adjust(2)
    return kb.as_markup()


def service_input_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Система", callback_data="menu:system")
    kb.adjust(1)
    return kb.as_markup()


def service_actions_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Start", callback_data="svc:start")
    kb.button(text="Stop", callback_data="svc:stop")
    kb.button(text="Restart", callback_data="svc:restart")
    kb.button(text="Сменить службу", callback_data="sys:services")
    kb.button(text="⬅️ Система", callback_data="menu:system")
    kb.adjust(3, 1, 1)
    return kb.as_markup()


def files_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="ТОП тяжелых", callback_data="files:heavy")
    kb.button(text="Скачать файл", callback_data="files:download")
    kb.button(text="⬅️ В главное", callback_data="menu:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def backups_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Бэкап папки", callback_data="backup:create")
    kb.button(text="⬅️ В главное", callback_data="menu:main")
    kb.adjust(1, 1)
    return kb.as_markup()


def terminal_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В главное меню", callback_data="term:exit")
    kb.adjust(1)
    return kb.as_markup()


def tools_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Мониторинг + алерты", callback_data="tools:alerts")
    kb.button(text="🧱 Файервол-профили", callback_data="tools:fw_profiles")
    kb.button(text="🧾 Журналы", callback_data="tools:logs")
    kb.button(text="🔒 Fail2ban", callback_data="tools:fail2ban")
    kb.button(text="🐳 Docker/Compose", callback_data="tools:docker")
    kb.button(text="⬆️ Обновления", callback_data="tools:updates")
    kb.button(text="💾 Бэкапы PRO", callback_data="tools:backup_pro")
    kb.button(text="👤 Админы", callback_data="tools:admins")
    kb.button(text="⬅️ В главное", callback_data="menu:main")
    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup()


def admins_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Список админов", callback_data="adm:list")
    kb.button(text="Добавить админа", callback_data="adm:add")
    kb.button(text="Удалить админа", callback_data="adm:remove")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(1, 2, 1)
    return kb.as_markup()


def alerts_menu(enabled: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"Статус: {'ON' if enabled else 'OFF'}", callback_data="al:toggle")
    kb.button(text="CPU порог", callback_data="al:set_cpu")
    kb.button(text="RAM порог", callback_data="al:set_ram")
    kb.button(text="Disk порог", callback_data="al:set_disk")
    kb.button(text="Интервал", callback_data="al:set_interval")
    kb.button(text="Cooldown", callback_data="al:set_cooldown")
    kb.button(text="Службы", callback_data="al:set_services")
    kb.button(text="Тест алерта", callback_data="al:test")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(1, 3, 2, 1, 1)
    return kb.as_markup()


def firewall_profiles_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Web", callback_data="fwp:ask:web")
    kb.button(text="SSH Only", callback_data="fwp:ask:ssh")
    kb.button(text="DB Closed", callback_data="fwp:ask:db")
    kb.button(text="Panic", callback_data="fwp:panic")
    kb.button(text="Показать правила", callback_data="fwp:show")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def firewall_profile_confirm_menu(profile: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Применить", callback_data=f"fwp:apply:{profile}")
    kb.button(text="❌ Отмена", callback_data="tools:fw_profiles")
    kb.adjust(2)
    return kb.as_markup()


def logs_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Auth", callback_data="logs:auth")
    kb.button(text="Kernel", callback_data="logs:kernel")
    kb.button(text="Errors", callback_data="logs:errors")
    kb.button(text="Служба", callback_data="logs:service")
    kb.button(text="Поиск", callback_data="logs:search")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(3, 2, 1)
    return kb.as_markup()


def fail2ban_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Статус", callback_data="f2b:status")
    kb.button(text="Список jail", callback_data="f2b:jails")
    kb.button(text="Статус jail", callback_data="f2b:jail_status")
    kb.button(text="Ban IP", callback_data="f2b:ban")
    kb.button(text="Unban IP", callback_data="f2b:unban")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def docker_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Docker info", callback_data="dock:info")
    kb.button(text="Контейнеры", callback_data="dock:containers")
    kb.button(text="Образы", callback_data="dock:images")
    kb.button(text="Set Compose Path", callback_data="dock:set_compose")
    kb.button(text="Compose PS", callback_data="dock:compose_ps")
    kb.button(text="Compose UP -d", callback_data="dock:compose_up")
    kb.button(text="Compose DOWN", callback_data="dock:compose_down")
    kb.button(text="Compose PULL", callback_data="dock:compose_pull")
    kb.button(text="Логи контейнера", callback_data="dock:logs")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(2, 2, 2, 2, 1, 1)
    return kb.as_markup()


def updates_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Проверить обновления", callback_data="upd:check")
    kb.button(text="Запустить upgrade", callback_data="upd:upgrade")
    kb.button(text="Очистка кэша", callback_data="upd:clean")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(1, 2, 1)
    return kb.as_markup()


def updates_confirm_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Запустить", callback_data="upd:upgrade:yes")
    kb.button(text="❌ Отмена", callback_data="tools:updates")
    kb.adjust(2)
    return kb.as_markup()


def backup_pro_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Создать backup", callback_data="bpro:create")
    kb.button(text="Список backup", callback_data="bpro:list")
    kb.button(text="Скачать backup", callback_data="bpro:download")
    kb.button(text="Восстановить backup", callback_data="bpro:restore")
    kb.button(text="Удалить backup", callback_data="bpro:delete")
    kb.button(text="⬅️ Инструменты", callback_data="menu:tools")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()
