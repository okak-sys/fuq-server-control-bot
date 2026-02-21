from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_ids: tuple[int, ...]
    command_timeout: int
    terminal_timeout: int
    firewall_safe_ports: tuple[int, ...]


def _parse_admin_ids(primary_admin: int, raw_extra: str) -> tuple[int, ...]:
    values: list[int] = [primary_admin]
    for chunk in raw_extra.replace(";", ",").split(","):
        token = chunk.strip()
        if not token:
            continue
        if token.isdigit():
            values.append(int(token))
    deduped: list[int] = []
    seen: set[int] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return tuple(deduped)


def _parse_ports(raw: str) -> tuple[int, ...]:
    ports: list[int] = []
    for chunk in raw.replace(";", ",").split(","):
        token = chunk.strip()
        if not token or not token.isdigit():
            continue
        value = int(token)
        if 1 <= value <= 65535:
            ports.append(value)
    deduped: list[int] = []
    seen: set[int] = set()
    for item in ports:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    if not deduped:
        deduped = [22, 80, 443]
    return tuple(deduped)


def load_settings() -> Settings:
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_raw = os.getenv("ADMIN_ID", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")
    if not admin_raw.isdigit():
        raise RuntimeError("ADMIN_ID must be numeric")
    primary_admin = int(admin_raw)
    extra_admins_raw = os.getenv("ADMIN_IDS", "").strip()
    command_timeout = int(os.getenv("COMMAND_TIMEOUT", "30"))
    terminal_timeout = int(os.getenv("TERMINAL_TIMEOUT", "60"))
    firewall_safe_ports = _parse_ports(os.getenv("FIREWALL_SAFE_PORTS", "22,80,443"))
    return Settings(
        bot_token=bot_token,
        admin_ids=_parse_admin_ids(primary_admin, extra_admins_raw),
        command_timeout=command_timeout,
        terminal_timeout=terminal_timeout,
        firewall_safe_ports=firewall_safe_ports,
    )
