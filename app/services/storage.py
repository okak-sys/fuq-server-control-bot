import asyncio
import copy
import json
import re
from pathlib import Path
from typing import Any

SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.@-]+$")

DEFAULT_DATA: dict[str, Any] = {
    "runtime": {
        "admin_chat_id": None,
        "compose_project": "",
        "extra_admin_ids": [],
        "firewall_safe_ports": [],
        "firewall_enabled": False,
    },
    "alerts": {
        "enabled": False,
        "cpu": 90,
        "ram": 90,
        "disk": 90,
        "interval": 30,
        "cooldown": 300,
        "services": [],
    },
}


def _clamp_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < low:
        return low
    if parsed > high:
        return high
    return parsed


def _normalize_services(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        if SERVICE_NAME_RE.fullmatch(text):
            result.append(text)
    seen: set[str] = set()
    deduped: list[str] = []
    for item in result:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:20]


def _normalize_admin_ids(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return []
    values: list[int] = []
    for item in raw:
        if isinstance(item, int) and item > 0:
            values.append(item)
        elif isinstance(item, str) and item.isdigit():
            values.append(int(item))
    deduped: list[int] = []
    seen: set[int] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:50]


def _normalize_ports(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return []
    values: list[int] = []
    for item in raw:
        if isinstance(item, int):
            value = item
        elif isinstance(item, str) and item.isdigit():
            value = int(item)
        else:
            continue
        if 1 <= value <= 65535:
            values.append(value)
    deduped: list[int] = []
    seen: set[int] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:50]


def normalize_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}
    alerts = data.get("alerts")
    if not isinstance(alerts, dict):
        alerts = {}
    admin_chat_id = runtime.get("admin_chat_id")
    if isinstance(admin_chat_id, int):
        admin_value = admin_chat_id
    elif isinstance(admin_chat_id, str) and admin_chat_id.isdigit():
        admin_value = int(admin_chat_id)
    else:
        admin_value = None
    compose_project = str(runtime.get("compose_project", "")).strip()
    return {
        "runtime": {
            "admin_chat_id": admin_value,
            "compose_project": compose_project,
            "extra_admin_ids": _normalize_admin_ids(runtime.get("extra_admin_ids", [])),
            "firewall_safe_ports": _normalize_ports(runtime.get("firewall_safe_ports", [])),
            "firewall_enabled": bool(runtime.get("firewall_enabled", False)),
        },
        "alerts": {
            "enabled": bool(alerts.get("enabled", False)),
            "cpu": _clamp_int(alerts.get("cpu"), 90, 1, 100),
            "ram": _clamp_int(alerts.get("ram"), 90, 1, 100),
            "disk": _clamp_int(alerts.get("disk"), 90, 1, 100),
            "interval": _clamp_int(alerts.get("interval"), 30, 10, 3600),
            "cooldown": _clamp_int(alerts.get("cooldown"), 300, 30, 86400),
            "services": _normalize_services(alerts.get("services", [])),
        },
    }


class Storage:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data") / "state.json"
        self._lock = asyncio.Lock()
        self._cache = self._load_sync()

    def _load_sync(self) -> dict[str, Any]:
        if not self.path.exists():
            return copy.deepcopy(DEFAULT_DATA)
        try:
            payload = self.path.read_text(encoding="utf-8")
            data = json.loads(payload)
        except Exception:
            return copy.deepcopy(DEFAULT_DATA)
        return normalize_data(data)

    def _save_sync(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return copy.deepcopy(self._cache)

    async def get_admin_chat_id(self) -> int | None:
        async with self._lock:
            value = self._cache["runtime"]["admin_chat_id"]
            return int(value) if isinstance(value, int) else None

    async def set_admin_chat_id(self, chat_id: int) -> None:
        async with self._lock:
            value = int(chat_id)
            if self._cache["runtime"]["admin_chat_id"] == value:
                return
            self._cache["runtime"]["admin_chat_id"] = value
            self._save_sync()

    async def get_compose_project(self) -> str:
        async with self._lock:
            return str(self._cache["runtime"]["compose_project"])

    async def set_compose_project(self, path: str) -> None:
        async with self._lock:
            value = path.strip()
            if self._cache["runtime"]["compose_project"] == value:
                return
            self._cache["runtime"]["compose_project"] = value
            self._save_sync()

    async def get_extra_admin_ids(self) -> list[int]:
        async with self._lock:
            return list(self._cache["runtime"]["extra_admin_ids"])

    async def add_admin_id(self, admin_id: int) -> list[int]:
        async with self._lock:
            current = list(self._cache["runtime"]["extra_admin_ids"])
            if admin_id not in current:
                current.append(admin_id)
            normalized = _normalize_admin_ids(current)
            if normalized != self._cache["runtime"]["extra_admin_ids"]:
                self._cache["runtime"]["extra_admin_ids"] = normalized
                self._save_sync()
            return list(self._cache["runtime"]["extra_admin_ids"])

    async def remove_admin_id(self, admin_id: int) -> list[int]:
        async with self._lock:
            current = [item for item in self._cache["runtime"]["extra_admin_ids"] if item != admin_id]
            normalized = _normalize_admin_ids(current)
            if normalized != self._cache["runtime"]["extra_admin_ids"]:
                self._cache["runtime"]["extra_admin_ids"] = normalized
                self._save_sync()
            return list(self._cache["runtime"]["extra_admin_ids"])

    async def is_admin(self, user_id: int, base_admin_ids: tuple[int, ...]) -> bool:
        async with self._lock:
            if user_id in base_admin_ids:
                return True
            return user_id in self._cache["runtime"]["extra_admin_ids"]

    async def list_admin_ids(self, base_admin_ids: tuple[int, ...]) -> list[int]:
        async with self._lock:
            values = list(base_admin_ids) + list(self._cache["runtime"]["extra_admin_ids"])
            deduped: list[int] = []
            seen: set[int] = set()
            for item in values:
                if item in seen:
                    continue
                seen.add(item)
                deduped.append(item)
            return deduped

    async def get_firewall_ports(self, fallback: tuple[int, ...]) -> list[int]:
        async with self._lock:
            current = list(self._cache["runtime"]["firewall_safe_ports"])
            if current:
                return current
            return list(fallback)

    async def set_firewall_ports(self, ports: list[int]) -> list[int]:
        async with self._lock:
            normalized = _normalize_ports(ports)
            if normalized != self._cache["runtime"]["firewall_safe_ports"]:
                self._cache["runtime"]["firewall_safe_ports"] = normalized
                self._save_sync()
            return list(normalized)

    async def get_firewall_enabled(self) -> bool:
        async with self._lock:
            return bool(self._cache["runtime"]["firewall_enabled"])

    async def set_firewall_enabled(self, enabled: bool) -> bool:
        async with self._lock:
            value = bool(enabled)
            if self._cache["runtime"]["firewall_enabled"] == value:
                return value
            self._cache["runtime"]["firewall_enabled"] = value
            self._save_sync()
            return bool(self._cache["runtime"]["firewall_enabled"])

    async def get_alerts(self) -> dict[str, Any]:
        async with self._lock:
            return copy.deepcopy(self._cache["alerts"])

    async def set_alert_value(self, key: str, value: Any) -> dict[str, Any]:
        async with self._lock:
            alerts = self._cache["alerts"]
            if key == "enabled":
                alerts["enabled"] = bool(value)
            elif key in {"cpu", "ram", "disk"}:
                alerts[key] = _clamp_int(value, alerts[key], 1, 100)
            elif key == "interval":
                alerts["interval"] = _clamp_int(value, alerts["interval"], 10, 3600)
            elif key == "cooldown":
                alerts["cooldown"] = _clamp_int(value, alerts["cooldown"], 30, 86400)
            self._save_sync()
            return copy.deepcopy(alerts)

    async def set_alert_services(self, values: list[str]) -> dict[str, Any]:
        async with self._lock:
            alerts = self._cache["alerts"]
            alerts["services"] = _normalize_services(values)
            self._save_sync()
            return copy.deepcopy(alerts)
