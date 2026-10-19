"""Non-destructive recovery of local copies archived by Drive para Linux.

Recovered items are copied into a separate directory and never written back
into the active mirror or Google Drive without the user's explicit action.
"""
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from background_sync import BACKUP_BASE, job_key
from sync_plan import validate_relative

@dataclass(frozen=True)
class RecoveryItem:
    path: Path
    relative: str
    label: str

def recovery_root(home=None, mirror_folder=None):
    home = Path.home() if home is None else Path(home)
    docs = home / ("Documentos" if (home / "Documentos").is_dir() else "Documents")
    proposed = docs / "DriveRecuperados"
    if mirror_folder is not None:
        mirror = Path(mirror_folder).expanduser().resolve()
        destination = proposed.resolve()
        if destination == mirror or destination in mirror.parents or mirror in destination.parents:
            return home / ".local" / "share" / "gdrive-linux" / "recovered"
    return proposed

def list_local_backups(remote, folder, backup_base=BACKUP_BASE, limit=30):
    base = Path(backup_base) / job_key(remote, Path(folder))
    if not base.is_dir():
        return []
    files = []
    for path in base.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        try:
            validate_relative(relative)
        except ValueError:
            continue
        files.append((path.stat().st_mtime_ns, RecoveryItem(path, relative, relative)))
    return [row[1] for row in sorted(files, key=lambda pair: pair[0], reverse=True)[:limit]]

def restore_local_backup(item, destination=None, mirror_folder=None):
    if not isinstance(item, RecoveryItem):
        raise ValueError("Selecione uma cópia de backup válida.")
    source = item.path
    if source.is_symlink() or not source.is_file():
        raise ValueError("A cópia de backup está indisponível ou é um link simbólico.")
    relative = validate_relative(item.relative)
    root = recovery_root(mirror_folder=mirror_folder) if destination is None else Path(destination).expanduser()
    root = root.resolve()
    if mirror_folder is not None:
        mirror = Path(mirror_folder).expanduser().resolve()
        if root == mirror or root in mirror.parents or mirror in root.parents:
            raise ValueError("Recuperação bloqueada: destino está dentro da pasta sincronizada.")
    target = root / relative
    if not target.resolve().is_relative_to(root):
        raise ValueError("Recuperação fora da pasta segura.")
    if target.is_symlink() or target.exists():
        raise ValueError("Já existe uma cópia no destino. Nenhum arquivo foi substituído.")
    parent = target.parent
    if parent.exists() and parent.is_symlink():
        raise ValueError("Diretório de recuperação inseguro.")
    parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    # O_EXCL avoids overwriting a file created concurrently by the user.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as origin:
            shutil.copyfileobj(origin, output)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target
