"""Local settings: never store OAuth tokens here."""
import json
import os
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
        return result
    except (OSError, ValueError, TypeError):
        return {}

def save_settings(folder, account="", account_names=None, auto_sync_enabled=False,
                  mount_read_only=True):
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    payload_data = {"folder": str(folder), "account": account,
                    "auto_sync_enabled": auto_sync_enabled is True,
                    "mount_read_only": mount_read_only is not False}
    if account_names:
        payload_data["account_names"] = {
            k: v for k, v in account_names.items()
            if isinstance(k, str) and isinstance(v, str)
            and len(k) <= 60 and len(v) <= 120
        }
    payload = json.dumps(payload_data, ensure_ascii=False)
    temporary = CONFIG_FILE.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temporary, CONFIG_FILE)
    finally:
        if temporary.exists():
            temporary.unlink()
