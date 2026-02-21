import asyncio
import hashlib
import re
import tarfile
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("/backup")
SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def build_backup_name(source: Path) -> str:
    base = source.name if source.name else "rootfs"
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", base).strip("_")
    if not safe:
        safe = "backup"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe}_{stamp}.tar.gz"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _extract_safe(archive: tarfile.TarFile, target: Path) -> int:
    target.mkdir(parents=True, exist_ok=True)
    target_resolved = target.resolve()
    members = archive.getmembers()
    for member in members:
        resolved = (target / member.name).resolve()
        if not str(resolved).startswith(str(target_resolved)):
            raise RuntimeError("Архив содержит небезопасный путь")
    archive.extractall(path=target)
    return len(members)


async def create_backup(source: Path) -> tuple[Path, int, str]:
    destination = ensure_backup_dir()
    archive_path = destination / build_backup_name(source)

    def _pack() -> None:
        arcname = source.name if source.name else "rootfs"
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(source, arcname=arcname)

    await asyncio.to_thread(_pack)
    checksum = await asyncio.to_thread(_sha256_file, archive_path)
    checksum_path = Path(f"{archive_path}.sha256")
    checksum_path.write_text(f"{checksum}  {archive_path.name}\n", encoding="utf-8")
    size_bytes = archive_path.stat().st_size
    return archive_path, size_bytes, checksum


def list_backups(limit: int = 20) -> list[tuple[str, int, datetime]]:
    destination = ensure_backup_dir()
    items: list[tuple[str, int, datetime]] = []
    for path in destination.glob("*.tar.gz"):
        stat = path.stat()
        items.append((path.name, stat.st_size, datetime.fromtimestamp(stat.st_mtime)))
    items.sort(key=lambda item: item[2], reverse=True)
    return items[:limit]


def resolve_backup_name(name: str) -> Path | None:
    clean = Path(name.strip()).name
    if not clean or "/" in clean or "\\" in clean:
        return None
    if not SAFE_NAME_RE.fullmatch(clean):
        return None
    path = ensure_backup_dir() / clean
    if path.exists() and path.is_file():
        return path
    return None


async def restore_backup(archive_path: Path, target: Path) -> int:
    def _restore() -> int:
        with tarfile.open(archive_path, "r:gz") as archive:
            return _extract_safe(archive, target)

    return await asyncio.to_thread(_restore)


def delete_backup(archive_path: Path) -> tuple[bool, str]:
    try:
        archive_path.unlink(missing_ok=False)
    except Exception as exc:
        return False, str(exc)
    checksum_path = Path(f"{archive_path}.sha256")
    try:
        checksum_path.unlink(missing_ok=True)
    except Exception:
        pass
    return True, "OK"
