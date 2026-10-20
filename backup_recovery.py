"""Non-destructive recovery of local copies archived by Drive para Linux.

Recovered items are copied into a separate directory and never written back
into the active mirror or Google Drive without the user's explicit action.
"""
import os
import stat
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
    """Restore into a private, unshared directory without following symlinks.

    Open the source using O_NOFOLLOW and create each destination directory
    relative to a verified parent file descriptor. A raced symbolic link can
    neither redirect the copy nor overwrite an existing user file.
    """
    if not isinstance(item, RecoveryItem):
        raise ValueError("Selecione uma cópia de backup válida.")
    relative = validate_relative(item.relative)
    source = Path(item.path)
    if source.is_symlink() or not source.is_file():
        raise ValueError("A cópia de backup está indisponível ou é um link simbólico.")
    root = recovery_root(mirror_folder=mirror_folder) if destination is None else Path(destination).expanduser()
    if root.is_symlink():
        raise ValueError("Diretório de recuperação simbólico não permitido.")
    root = root.resolve()
    if mirror_folder is not None:
        mirror = Path(mirror_folder).expanduser().resolve()
        if root == mirror or root in mirror.parents or mirror in root.parents:
            raise ValueError("Recuperação bloqueada: destino está dentro da pasta sincronizada.")
    target = root / relative
    if not target.resolve().is_relative_to(root):
        raise ValueError("Recuperação fora da pasta segura.")
    if target.exists() or target.is_symlink():
        raise ValueError("Já existe uma cópia no destino. Nenhum arquivo foi substituído.")
    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("Sistema sem proteção necessária contra links simbólicos.")
    read_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    dir_flags = read_flags | os.O_DIRECTORY
    input_fd = os.open(source, read_flags)
    try:
        identity = os.fstat(input_fd)
        if not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1:
            raise ValueError("Cópia de recuperação não é um arquivo regular independente.")
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        dir_fd = os.open(root, dir_flags)
        try:
            for part in Path(relative).parts[:-1]:
                try:
                    os.mkdir(part, 0o700, dir_fd=dir_fd)
                except FileExistsError:
                    pass
                next_fd = os.open(part, dir_flags, dir_fd=dir_fd)
                os.close(dir_fd)
                dir_fd = next_fd
            name = Path(relative).name
            try:
                output_fd = os.open(
                    name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                    | getattr(os, "O_CLOEXEC", 0), 0o600, dir_fd=dir_fd)
            except FileExistsError as exc:
                raise ValueError(
                    "Já existe uma cópia no destino. Nenhum arquivo foi substituído.") from exc
            try:
                with os.fdopen(os.dup(input_fd), "rb") as origin, os.fdopen(output_fd, "wb") as output:
                    shutil.copyfileobj(origin, output, length=1024*1024)
                    output.flush()
                    os.fsync(output.fileno())
                os.fsync(dir_fd)
            except BaseException:
                os.unlink(name, dir_fd=dir_fd)
                raise
        finally:
            os.close(dir_fd)
    finally:
        os.close(input_fd)
    return target
