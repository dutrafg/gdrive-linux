"""Non-destructive synchronization planning and conflict detection."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
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
    if not isinstance(path, str) or not path or path.startswith("/"):
        raise ValueError("Caminho inválido")
    parts = Path(path).parts
    if path.startswith("./") or "//" in path or path.endswith("/") or ":" in path.split("/")[0]:
        raise ValueError("Caminho inválido")
    if any(p in (".", "..") for p in parts) or "\x00" in path or "\\" in path:
        raise ValueError("Caminho inválido")
    return path

def local_inventory(folder):
    root = Path(folder).resolve()
    if not root.is_dir():
        raise ValueError("Pasta local inexistente")
    found = {}
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        validate_relative(relative)
        digest = hashlib.md5()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        found[relative] = ("md5", digest.hexdigest())
    return found

def remote_inventory(remote, timeout=120):
    from rclone_backend import remote_path
    cmd = ["rclone", "lsjson", remote_path(remote), "--recursive", "--files-only",
           "--hash", "--exclude", "/.gdrive-linux-history/**",
           "--exclude", "/.gdrive-linux-backups/**"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout)
    records = json.loads(result.stdout)
    if not isinstance(records, list):
        raise ValueError("Inventário remoto inválido")
    found = {}
    for item in records:
        path = validate_relative(item["Path"])
        if path.split("/", 1)[0] in (".gdrive-linux-history", ".gdrive-linux-backups"):
            continue
        hashes = item.get("Hashes") or {}
        digest = hashes.get("MD5") or hashes.get("SHA-256")
        if digest:
            found[path] = ("md5" if hashes.get("MD5") else "sha256", digest.lower())
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
