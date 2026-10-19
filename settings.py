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
        return {key: data[key] for key in ("folder", "account") if isinstance(data.get(key), str)}
    except (OSError, ValueError, TypeError):
        return {}

def save_settings(folder, account=""):
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    payload = json.dumps({"folder": str(folder), "account": account}, ensure_ascii=False)
    temporary = CONFIG_FILE.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temporary, CONFIG_FILE)
    finally:
        if temporary.exists():
            temporary.unlink()
