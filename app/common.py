import html
import ipaddress
import re
from datetime import datetime
from pathlib import Path

from app.services.formatting import pre
from app.services.shell import ExecResult, run_exec

SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.@-]+$")
CONTAINER_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def compact_status(result: ExecResult) -> str:
    if result.timed_out:
        return "TIMEOUT"
    if result.returncode == 0:
        return "OK"
    return f"ERR {result.returncode}"


def compact_report(title: str, entries: list[tuple[str, ExecResult]]) -> str:
    parts = [f"<b>{html.escape(title)}</b>"]
    for label, result in entries:
        details = result.stderr.strip() or result.stdout.strip() or "(пусто)"
        parts.append(f"<b>{html.escape(label)}:</b> {compact_status(result)}")
        parts.append(pre(details, limit=700))
    return "\n".join(parts)


def parse_port(value: str) -> int | None:
    if not value.isdigit():
        return None
    port = int(value)
    if 1 <= port <= 65535:
        return port
    return None


def parse_ports_csv(value: str) -> list[int]:
    ports: list[int] = []
    for chunk in value.replace(";", ",").split(","):
        token = chunk.strip()
        if not token.isdigit():
            continue
        port = int(token)
        if 1 <= port <= 65535:
            ports.append(port)
    deduped: list[int] = []
    seen: set[int] = set()
    for item in ports:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def parse_pid(value: str) -> int | None:
    if not value.isdigit():
        return None
    pid = int(value)
    if pid > 0:
        return pid
    return None


def parse_percent(value: str) -> int | None:
    if not value.isdigit():
        return None
    num = int(value)
    if 1 <= num <= 100:
        return num
    return None


def parse_interval(value: str, low: int, high: int) -> int | None:
    if not value.isdigit():
        return None
    num = int(value)
    if low <= num <= high:
        return num
    return None


def parse_ip(value: str) -> str | None:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return None
    return value


def normalize_heavy_files(raw: str) -> str:
    rows: list[str] = []
    for line in raw.splitlines():
        if "\t" in line:
            size_raw, path = line.split("\t", 1)
            if size_raw.isdigit():
                rows.append(f"{int(size_raw) / 1024**2:8.1f} MB  {path}")
                continue
        rows.append(line)
    return "\n".join(rows) if rows else "(пусто)"


def format_backups(items: list[tuple[str, int, datetime]]) -> str:
    if not items:
        return "<b>Бэкапы</b>\n(пусто)"
    lines: list[str] = []
    for name, size, modified in items:
        lines.append(f"{modified.strftime('%Y-%m-%d %H:%M')}  {size / 1024**2:8.1f} MB  {name}")
    return f"<b>Бэкапы (последние)</b>\n{pre('\n'.join(lines), limit=3200)}"


def resolve_compose_file(raw_path: str) -> Path | None:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        return None
    allowed = {"docker-compose.yml", "compose.yml", "compose.yaml"}
    if path.exists() and path.is_file() and path.name in allowed:
        return path
    if path.exists() and path.is_dir():
        for name in ("docker-compose.yml", "compose.yml", "compose.yaml"):
            candidate = path / name
            if candidate.exists() and candidate.is_file():
                return candidate
    return None


async def run_labeled_commands(
    commands: list[tuple[str, list[str]]],
    timeout: int,
) -> list[tuple[str, ExecResult]]:
    results: list[tuple[str, ExecResult]] = []
    for label, command in commands:
        result = await run_exec(command, timeout=timeout)
        results.append((label, result))
    return results


def labeled_report(title: str, entries: list[tuple[str, ExecResult]]) -> str:
    lines = [f"<b>{html.escape(title)}</b>"]
    for label, result in entries:
        lines.append(f"<b>{html.escape(label)}:</b> {compact_status(result)}")
        if result.returncode != 0 or result.stderr.strip():
            details = result.stderr.strip() or result.stdout.strip() or "(пусто)"
            lines.append(pre(details, limit=500))
    return "\n".join(lines)


def _base_firewall_commands() -> list[tuple[str, list[str]]]:
    return [
        ("Flush", ["iptables", "-F"]),
        ("Delete user chains", ["iptables", "-X"]),
        ("Policy INPUT DROP", ["iptables", "-P", "INPUT", "DROP"]),
        ("Policy FORWARD DROP", ["iptables", "-P", "FORWARD", "DROP"]),
        ("Policy OUTPUT ACCEPT", ["iptables", "-P", "OUTPUT", "ACCEPT"]),
        ("Allow ESTABLISHED", ["iptables", "-A", "INPUT", "-m", "conntrack", "--ctstate", "ESTABLISHED,RELATED", "-j", "ACCEPT"]),
        ("Allow loopback", ["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"]),
        ("Allow ICMP", ["iptables", "-A", "INPUT", "-p", "icmp", "-j", "ACCEPT"]),
    ]


async def apply_firewall_safe_mode(ports: list[int], timeout: int) -> str:
    commands = _base_firewall_commands()
    for port in ports:
        commands.append((f"Allow {port}/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"]))
        commands.append((f"Allow {port}/udp", ["iptables", "-A", "INPUT", "-p", "udp", "--dport", str(port), "-j", "ACCEPT"]))
    result = await run_labeled_commands(commands, timeout=timeout)
    ports_text = ", ".join(str(item) for item in ports) if ports else "(не заданы)"
    return labeled_report(f"Фаервол включен, порты: {ports_text}", result)


async def disable_firewall(timeout: int) -> str:
    commands = [
        ("Flush", ["iptables", "-F"]),
        ("Delete user chains", ["iptables", "-X"]),
        ("Policy INPUT ACCEPT", ["iptables", "-P", "INPUT", "ACCEPT"]),
        ("Policy FORWARD ACCEPT", ["iptables", "-P", "FORWARD", "ACCEPT"]),
        ("Policy OUTPUT ACCEPT", ["iptables", "-P", "OUTPUT", "ACCEPT"]),
    ]
    result = await run_labeled_commands(commands, timeout=timeout)
    return labeled_report("Фаервол выключен", result)


async def apply_firewall_profile(profile: str, timeout: int, admin_ip: str | None = None) -> str:
    commands: list[tuple[str, list[str]]] = _base_firewall_commands()
    if profile == "web":
        commands.extend(
            [
                ("Allow SSH 22/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "22", "-j", "ACCEPT"]),
                ("Allow HTTP 80/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"]),
                ("Allow HTTPS 443/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "443", "-j", "ACCEPT"]),
            ]
        )
    elif profile == "ssh":
        commands.append(("Allow SSH 22/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "22", "-j", "ACCEPT"]))
    elif profile == "db":
        commands.extend(
            [
                ("Allow SSH 22/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "22", "-j", "ACCEPT"]),
                ("Allow HTTP 80/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "80", "-j", "ACCEPT"]),
                ("Allow HTTPS 443/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "443", "-j", "ACCEPT"]),
                ("Drop MySQL 3306/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "3306", "-j", "DROP"]),
                ("Drop PostgreSQL 5432/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "5432", "-j", "DROP"]),
                ("Drop Redis 6379/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "6379", "-j", "DROP"]),
                ("Drop MongoDB 27017/tcp", ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "27017", "-j", "DROP"]),
            ]
        )
    elif profile == "panic" and admin_ip:
        commands.append(("Allow SSH from admin IP", ["iptables", "-A", "INPUT", "-p", "tcp", "-s", admin_ip, "--dport", "22", "-j", "ACCEPT"]))
    else:
        return "<b>Неизвестный профиль</b>"
    result = await run_labeled_commands(commands, timeout=timeout)
    return labeled_report(f"Файервол-профиль: {profile.upper()}", result)
