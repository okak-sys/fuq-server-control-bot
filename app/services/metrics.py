from datetime import datetime

import psutil


def _human_uptime(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days > 0:
        return f"{days}д {hours:02}:{minutes:02}:{secs:02}"
    return f"{hours:02}:{minutes:02}:{secs:02}"


def system_metrics_text() -> str:
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    uptime_seconds = int(datetime.now().timestamp() - psutil.boot_time())
    return (
        "<b>Системные метрики</b>\n"
        f"<b>CPU:</b> {cpu:.1f}%\n"
        f"<b>RAM:</b> {mem.percent:.1f}% ({mem.used / 1024**3:.2f} / {mem.total / 1024**3:.2f} GB)\n"
        f"<b>Disk /:</b> {disk.percent:.1f}% ({disk.used / 1024**3:.2f} / {disk.total / 1024**3:.2f} GB)\n"
        f"<b>Uptime:</b> {_human_uptime(uptime_seconds)}\n"
        f"<b>Обновлено:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
