"""Validated multi-account, per-folder rclone synchronization profiles."""
from pathlib import Path
from rclone_backend import remote_path
from sync_filters import parse_rules

MODES = ("bidirectional", "upload", "download")
MAX_PROFILES = 12

def validate_mode(mode):
    if mode not in MODES:
        raise ValueError("Modo de sincronização desconhecido.")
    return mode

def normalize_profile(item):
    if not isinstance(item, dict):
        raise ValueError("Perfil inválido.")
    remote = item.get("account")
    remote_path(remote)  # Validate against rclone remote rules.
    value = item.get("folder")
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("Selecione uma pasta para esta conta.")
    folder = Path(value).expanduser().resolve()
    if folder == Path(folder.anchor):
        raise ValueError("Não sincronize a raiz do disco.")
    return {
        "account": remote, "folder": str(folder),
        "mode": validate_mode(item.get("mode", "bidirectional")),
        "sync_includes": parse_rules(item.get("sync_includes", [])),
        "sync_excludes": parse_rules(item.get("sync_excludes", [])),
        "auto_archive_deletions": item.get("auto_archive_deletions") is True,
        "enabled": item.get("enabled") is not False,
    }

def validate_profiles(value):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_PROFILES:
        raise ValueError("Configure até 12 contas independentes.")
    profiles = [normalize_profile(p) for p in value]
    for i, left in enumerate(profiles):
        if not left["enabled"]:
            continue
        la = Path(left["folder"])
        for right in profiles[i + 1:]:
            if not right["enabled"]:
                continue
            rb = Path(right["folder"])
            if (la == rb or la in rb.parents or rb in la.parents):
                raise ValueError("Perfis ativos não podem usar pastas iguais ou aninhadas.")
            if left["account"] == right["account"]:
                raise ValueError("A mesma conta remota não pode ter dois espelhos ativos.")
    return profiles

def effective_profiles(settings):
    """Legacy settings remain supported until user adds explicit profiles."""
    if not settings.get("auto_sync_enabled"):
        return []
    jobs = validate_profiles(settings.get("sync_profiles"))
    if jobs:
        return jobs
    if settings.get("sync_profiles") == [] and settings.get("profiles_configured"):
        return []
    return [normalize_profile({
        "account": settings.get("account"),
        "folder": settings.get("folder"),
        "mode": settings.get("sync_mode", "bidirectional"),
        "sync_includes": settings.get("sync_includes", []),
        "sync_excludes": settings.get("sync_excludes", []),
        "auto_archive_deletions": settings.get("auto_archive_deletions", False),
    })]

def get_profile_mode(settings):
    return validate_mode(settings.get("mode", "bidirectional"))
