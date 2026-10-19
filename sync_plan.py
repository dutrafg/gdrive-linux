"""Non-destructive synchronization planning and conflict detection."""
from dataclasses import dataclass
from pathlib import Path

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
    if any(p in (".", "..") for p in parts) or "\x00" in path or "\\" in path:
        raise ValueError("Caminho inválido")
    return path
