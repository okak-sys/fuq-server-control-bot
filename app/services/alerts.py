import html
import time
from typing import Any

import psutil
from aiogram import Bot

from app.services.shell import run_exec
from app.services.storage import Storage


class AlertsEngine:
    def __init__(self, bot: Bot, storage: Storage, command_timeout: int) -> None:
        self.bot = bot
        self.storage = storage
        self.command_timeout = command_timeout
        self.last_sent: dict[str, float] = {}
        self.active: dict[str, bool] = {}

    async def _notify(self, chat_id: int, text: str) -> None:
        await self.bot.send_message(chat_id=chat_id, text=text)

    async def _evaluate(
        self,
        chat_id: int,
        key: str,
        triggered: bool,
        alarm_text: str,
        recover_text: str,
        cooldown: int,
    ) -> None:
        now = time.monotonic()
        was_active = self.active.get(key, False)
        if triggered:
            last = self.last_sent.get(key, 0.0)
            if (not was_active) or (now - last >= cooldown):
                await self._notify(chat_id, alarm_text)
                self.last_sent[key] = now
            self.active[key] = True
            return
        if was_active:
            await self._notify(chat_id, recover_text)
            self.last_sent[key] = now
        self.active[key] = False

    async def check_once(self) -> None:
        config = await self.storage.get_alerts()
        if not config["enabled"]:
            return
        chat_id = await self.storage.get_admin_chat_id()
        if not chat_id:
            return
        cooldown = int(config["cooldown"])
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        await self._evaluate(
            chat_id,
            "metric:cpu",
            cpu >= config["cpu"],
            f"🚨 CPU выше порога: {cpu:.1f}% (порог {config['cpu']}%)",
            f"✅ CPU нормализован: {cpu:.1f}% (порог {config['cpu']}%)",
            cooldown,
        )
        await self._evaluate(
            chat_id,
            "metric:ram",
            ram >= config["ram"],
            f"🚨 RAM выше порога: {ram:.1f}% (порог {config['ram']}%)",
            f"✅ RAM нормализована: {ram:.1f}% (порог {config['ram']}%)",
            cooldown,
        )
        await self._evaluate(
            chat_id,
            "metric:disk",
            disk >= config["disk"],
            f"🚨 Disk / выше порога: {disk:.1f}% (порог {config['disk']}%)",
            f"✅ Disk / нормализован: {disk:.1f}% (порог {config['disk']}%)",
            cooldown,
        )
        services: list[str] = list(config.get("services", []))
        for service in services:
            result = await run_exec(
                ["systemctl", "is-active", service],
                timeout=max(10, self.command_timeout),
            )
            status = result.stdout.strip() or result.stderr.strip() or "unknown"
            triggered = result.returncode != 0 or status != "active"
            escaped = html.escape(service)
            await self._evaluate(
                chat_id,
                f"service:{service}",
                triggered,
                f"🚨 Служба <code>{escaped}</code> неактивна: <b>{html.escape(status)}</b>",
                f"✅ Служба <code>{escaped}</code> снова активна",
                cooldown,
            )

    async def run(self) -> None:
        while True:
            config = await self.storage.get_alerts()
            interval = int(config["interval"])
            try:
                await self.check_once()
            except Exception as exc:
                chat_id = await self.storage.get_admin_chat_id()
                if chat_id:
                    await self._notify(chat_id, f"⚠️ Ошибка цикла алертов: <code>{html.escape(str(exc))}</code>")
            await self._sleep(interval)

    async def _sleep(self, interval: int) -> None:
        import asyncio

        await asyncio.sleep(max(10, min(interval, 3600)))
