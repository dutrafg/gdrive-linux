"""Local settings: never store OAuth tokens here."""
import json
import os
import tempfile
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "gdrive-linux"
CONFIG_FILE = CONFIG_DIR / "settings.json"

def load_settings():
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        result = {key: data[key] for key in ("folder", "account")
                  if isinstance(data.get(key), str)}
        names = data.get("account_names")
        if isinstance(names, dict):
            result["account_names"] = {
                key: value for key, value in names.items()
                if isinstance(key, str) and isinstance(value, str)
                and len(key) <= 60 and len(value) <= 120
            }
        result["auto_sync_enabled"] = data.get("auto_sync_enabled") is True
        result["mount_read_only"] = data.get("mount_read_only") is not False
        result["auto_archive_deletions"] = data.get("auto_archive_deletions") is True
        from sync_filters import parse_rules
        result["sync_includes"] = parse_rules(data.get("sync_includes", []))
        result["sync_excludes"] = parse_rules(data.get("sync_excludes", []))
        from sync_profiles import validate_mode, validate_profiles
        result["sync_mode"] = validate_mode(data.get("sync_mode", "bidirectional"))
        result["sync_profiles"] = validate_profiles(data.get("sync_profiles", []))
        result["profiles_configured"] = data.get("profiles_configured") is True
        from rclone_config import normalize_config_path
        configured = data.get("rclone_config_file", "")
        result["rclone_config_file"] = normalize_config_path(configured) if configured else ""
        return result
    except (OSError, ValueError, TypeError):
        return {}

def save_settings(folder, account="", account_names=None, auto_sync_enabled=False,
                  mount_read_only=True, auto_archive_deletions=False,
                  sync_includes=None, sync_excludes=None,
                  sync_mode="bidirectional", sync_profiles=None,
                  profiles_configured=False, rclone_config_file=""):
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    from sync_filters import parse_rules
    includes = parse_rules(sync_includes)
    excludes = parse_rules(sync_excludes)
    from sync_profiles import validate_profiles, validate_mode
    profiles = validate_profiles(sync_profiles)
    mode = validate_mode(sync_mode)
    from rclone_config import normalize_config_path
    selected_config = normalize_config_path(rclone_config_file)
    payload_data = {"folder": str(folder), "account": account,
                    "auto_sync_enabled": auto_sync_enabled is True,
                    "mount_read_only": mount_read_only is not False,
                    "auto_archive_deletions": auto_archive_deletions is True,
                    "sync_includes": includes, "sync_excludes": excludes,
                    "sync_mode": mode, "sync_profiles": profiles,
                    "profiles_configured": profiles_configured is True,
                    "rclone_config_file": selected_config}
    if account_names:
        payload_data["account_names"] = {
            k: v for k, v in account_names.items()
            if isinstance(k, str) and isinstance(v, str)
            and len(k) <= 60 and len(v) <= 120
        }
    payload = json.dumps(payload_data, ensure_ascii=False)
    # Unique temporary files prevent simultaneous UI/service settings writes
    # from trampling a fixed .tmp filename. Existing settings survive failures.
    fd, temporary = tempfile.mkstemp(prefix=".settings-", dir=CONFIG_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, CONFIG_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
