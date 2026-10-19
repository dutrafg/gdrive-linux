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
    source_folder = Path(value).expanduser()
    if source_folder.is_symlink():
        raise ValueError("Não configure uma pasta de sincronização simbólica.")
    folder = source_folder.resolve()
    if folder == Path.home().resolve() or folder in Path.home().resolve().parents:
        raise ValueError("Selecione uma subpasta exclusiva; não sincronize toda a pasta pessoal.")
    if folder == Path(folder.anchor):
        raise ValueError("Não sincronize a raiz do disco.")
    online = (Path.home() / "DriveOnline").resolve()
    if folder == online or online in folder.parents:
        raise ValueError("Não sincronize a montagem FUSE dentro do espelho local.")
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

def ensure_external_volume_present(folder):
    """Prevent writing into a removable-drive mountpoint when unplugged."""
    folder = Path(folder).expanduser().resolve()
    parts = folder.parts
    expected = None
    # Zorin/GNOME: /media/<user>/<disk>/<directory>
    if len(parts) >= 4 and parts[1] == "media":
        expected = Path("/", *parts[1:4])
    # Some other Linux desktops: /run/media/<user>/<disk>/...
    elif len(parts) >= 5 and parts[1:3] == ("run", "media"):
        expected = Path("/", *parts[1:5])
    if expected is not None and not expected.is_mount():
        raise ValueError("O disco externo selecionado não está montado. "
                         "Conecte-o antes de sincronizar; nenhum arquivo será alterado.")
    return True
