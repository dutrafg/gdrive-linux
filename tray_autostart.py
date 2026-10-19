"""Opt-in tray indicator autostart registration for the current Linux user."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ENTRY_NAME = "gdrive-linux-indicator.desktop"
MANAGED_TAG = "X-DriveLinux-Managed=true"

def indicator_available(runner=None):
    """Check GTK3 AppIndicator in a separate Python process to avoid GTK4 conflicts."""
    runner = subprocess.run if runner is None else runner
    probe = ("import gi\n"
             "gi.require_version('Gtk', '3.0')\n"
             "try:\n"
             " gi.require_version('AyatanaAppIndicator3', '0.1')\n"
             "except (ValueError, ImportError):\n"
             " gi.require_version('AppIndicator3', '0.1')\n")
    try:
        result = runner(
            ["/usr/bin/python3", "-c", probe], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=8)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False

def user_entry(home=None):
    return (Path(home) if home else Path.home()) / ".config" / "autostart" / ENTRY_NAME

def indicator_enabled(home=None):
    dest = user_entry(home)
    try:
        return MANAGED_TAG in dest.read_text(encoding="utf-8")
    except OSError:
        return False

def set_indicator_autostart(enable, source=None, home=None):
    if type(enable) is not bool:
        raise ValueError("Opção inválida.")
    dest = user_entry(home)
    if not enable:
        if dest.exists() and not indicator_enabled(home):
            raise ValueError("Entrada de inicialização não pertence a este aplicativo.")
        if dest.exists():
            dest.unlink()
        return False
    source = Path(source) if source else Path("/usr/share/applications") / ENTRY_NAME
    data = source.read_text(encoding="utf-8")
    if MANAGED_TAG not in data:
        raise ValueError("Atalho de inicialização inválido.")
    if dest.exists() and not indicator_enabled(home):
        raise ValueError("Existe um atalho com o mesmo nome, não será sobrescrito.")
    dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".gdrive-indicator-", dir=dest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
        os.chmod(tmp, 0o600)
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True
