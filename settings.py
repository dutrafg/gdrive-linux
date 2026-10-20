"""Local settings: never store OAuth tokens here."""
import json
import os
import tempfile
import stat
import fcntl
import threading
from contextlib import contextmanager
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "gdrive-linux"
CONFIG_FILE = CONFIG_DIR / "settings.json"
_SETTINGS_THREAD_LOCK = threading.RLock()

@contextmanager
def _serialized_settings_write():
    """Protect settings across GUI threads and separate background processes."""
    with _SETTINGS_THREAD_LOCK:
        if CONFIG_DIR.is_symlink():
            raise ValueError("Diretório de configurações inseguro: link simbólico.")
        CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        if CONFIG_DIR.is_symlink() or not CONFIG_DIR.is_dir():
            raise ValueError("Diretório de configurações inválido.")
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
        if not hasattr(os, "O_NOFOLLOW"):
            raise RuntimeError("O sistema não oferece trava segura para configurações.")
        fd = os.open(CONFIG_DIR / "config-write.lock", flags | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a+") as lock:
            status = os.fstat(lock.fileno())
            if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
                raise ValueError("Trava de configurações insegura.")
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def load_settings():
    try:
        if CONFIG_DIR.is_symlink() or CONFIG_FILE.is_symlink():
            return {}
        if CONFIG_FILE.exists() and (
                not CONFIG_FILE.is_file() or CONFIG_FILE.stat().st_nlink != 1
                or CONFIG_FILE.stat().st_size > 8 * 1024 * 1024):
            return {}
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
        result["rclone_config_file"] = normalize_config_path(configured, require_exists=False) if configured else ""
        return result
    except (OSError, ValueError, TypeError):
        return {}

def save_settings(folder, account="", account_names=None, auto_sync_enabled=False,
                  mount_read_only=True, auto_archive_deletions=False,
                  sync_includes=None, sync_excludes=None,
                  sync_mode="bidirectional", sync_profiles=None,
                  profiles_configured=False, rclone_config_file=""):
    with _serialized_settings_write():
        if CONFIG_DIR.is_symlink():
            raise ValueError("Diretório de configurações inseguro: link simbólico.")
        CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        if CONFIG_DIR.is_symlink() or not CONFIG_DIR.is_dir():
            raise ValueError("Diretório de configurações inválido.")
        os.chmod(CONFIG_DIR, 0o700)
        if CONFIG_FILE.is_symlink() or (CONFIG_FILE.exists() and
                (not CONFIG_FILE.is_file() or CONFIG_FILE.stat().st_nlink != 1)):
            raise ValueError("Arquivo de configurações inseguro; não será substituído.")
        from sync_filters import parse_rules
        includes = parse_rules(sync_includes)
        excludes = parse_rules(sync_excludes)
        from sync_profiles import validate_profiles, validate_mode
        profiles = validate_profiles(sync_profiles)
        mode = validate_mode(sync_mode)
        from rclone_config import normalize_config_path
        selected_config = normalize_config_path(rclone_config_file, require_exists=False)
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
            dir_fd = os.open(CONFIG_DIR, os.O_RDONLY | os.O_DIRECTORY |
                             getattr(os, "O_NOFOLLOW", 0))
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
