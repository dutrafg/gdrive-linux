"""Non-destructive synchronization planning and conflict detection."""
from dataclasses import dataclass
from pathlib import Path
from rclone_errors import rclone_limits
import hashlib
import json
import os
import re
import stat
import subprocess

@dataclass(frozen=True)
class SyncPlan:
    download: tuple
    upload: tuple
    conflicts: tuple

def plan_sync(local, remote):
    """Compare path -> fingerprint maps; never silently overwrite shared paths."""
    local_keys, remote_keys = set(local), set(remote)
    shared = local_keys & remote_keys
    return SyncPlan(
        download=tuple(sorted(remote_keys - local_keys)),
        upload=tuple(sorted(local_keys - remote_keys)),
        conflicts=tuple(sorted(k for k in shared if local[k] != remote[k])),
    )

def validate_relative(path):
    """Validate exact raw paths, not normalized Path.parts (which erases './')."""
    if not isinstance(path, str) or not path or path.startswith("/"):
        raise ValueError("Caminho inválido")
    if (path.startswith("./") or "//" in path or path.endswith("/")
            or ":" in path.split("/")[0] or "\\" in path
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in path)
            or len(path.encode("utf-8", "surrogatepass")) > 4096):
        raise ValueError("Caminho inválido")
    parts = path.split("/")
    if any(p in ("", ".", "..") or len(p.encode("utf-8", "surrogatepass")) > 255
           for p in parts):
        raise ValueError("Caminho inválido")
    return path

def local_inventory(folder):
    selected = Path(folder).expanduser()
    if selected.is_symlink():
        raise ValueError("A pasta espelhada não pode ser link simbólico")
    root = selected.resolve()
    if not root.is_dir():
        raise ValueError("Pasta local inexistente")
    found = {}
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        validate_relative(relative)
        # Do not follow a file replaced by a symlink between rglob and open.
        if not hasattr(os, "O_NOFOLLOW"):
            raise RuntimeError("Este Linux não oferece abertura segura sem links simbólicos.")
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(path, flags)
        except FileNotFoundError:
            raise RuntimeError("Arquivo desapareceu durante o inventário; repetir a verificação.")
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError("Arquivo inseguro ou com links rígidos dentro do espelho.")
            digest = hashlib.md5()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                 after.st_ctime_ns)):
                raise RuntimeError("Arquivo alterado durante o inventário; sincronização suspensa.")
        found[relative] = ("md5", digest.hexdigest())
    return found

def remote_inventory(remote, timeout=120):
    from rclone_backend import remote_path
    cmd = ["rclone", "lsjson", remote_path(remote), "--recursive", "--files-only",
           "--hash", "--exclude", "/.gdrive-linux-history/**",
           "--exclude", "/.gdrive-linux-backups/**"] + rclone_limits()
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout)
    records = json.loads(result.stdout)
    if not isinstance(records, list):
        raise ValueError("Inventário remoto inválido")
    found = {}
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get("Path"), str):
            raise ValueError("Inventário remoto contém registro inválido")
        path = validate_relative(item["Path"])
        if path.split("/", 1)[0] in (".gdrive-linux-history", ".gdrive-linux-backups"):
            continue
        if path in found:
            raise ValueError("Inventário remoto duplicou o mesmo caminho; sincronização interrompida")
        hashes = item.get("Hashes") or {}
        if not isinstance(hashes, dict):
            raise ValueError("Hash remoto inválido")
        md5, sha256 = hashes.get("MD5"), hashes.get("SHA-256")
        if md5 is not None and not re.fullmatch(r"[0-9a-fA-F]{32}", str(md5)):
            raise ValueError("MD5 remoto inválido")
        if sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(sha256)):
            raise ValueError("SHA256 remoto inválido")
        if md5:
            found[path] = ("md5", md5.lower())
        elif sha256:
            found[path] = ("sha256", sha256.lower())
        else:
            found[path] = ("metadata", str(item.get("Size")), str(item.get("ModTime")))
    return found

def conservative_plan(local, remote):
    """Different hash algorithms are incomparable: flag as conflict."""
    shared = set(local) & set(remote)
    comparable = {key for key in shared if local[key][0] == remote[key][0]}
    conflicts = sorted((shared - comparable) | {key for key in comparable if local[key] != remote[key]})
    return SyncPlan(tuple(sorted(set(remote) - set(local))),
                    tuple(sorted(set(local) - set(remote))), tuple(conflicts))
