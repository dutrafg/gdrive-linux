"""Consistent user-owned rclone configuration for GTK4 and systemd workers.

No tokens or file contents are read or persisted here. Only a path to
rclone.conf is stored; rclone itself owns the OAuth secrets.
"""
import os
from pathlib import Path

def normalize_config_path(value):
    if value in (None, ""):
        return ""
    if not isinstance(value, str) or "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("Caminho da configuração rclone inválido.")
    result = Path(value).expanduser().resolve()
    if not result.is_file():
        raise ValueError("Arquivo rclone.conf não existe.")
    return str(result)

def selected_config_path(settings, environment=None):
    environment = os.environ if environment is None else environment
    configured = settings.get("rclone_config_file") or environment.get("RCLONE_CONFIG")
    return normalize_config_path(configured) if configured else ""

def activate_worker_config(settings, environment=None):
    """Set environment only at worker startup, before any threads begin."""
    environment = os.environ if environment is None else environment
    selected = selected_config_path(settings, environment)
    if selected:
        environment["RCLONE_CONFIG"] = selected
    return selected
