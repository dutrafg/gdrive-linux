"""Optional one-way image/video export to a user-configured Google Photos rclone remote.

Google Photos is NOT a Google Drive folder and its API does not support full
library restoration. This module never deletes, downloads, or auto-syncs.
"""
import json
import re
import subprocess
from pathlib import Path

from rclone_backend import remote_path

ALBUM_NAME = re.compile(r"^[\wÀ-ÿ][\wÀ-ÿ ._-]{0,59}$", re.UNICODE)
PHOTO_EXTENSIONS = (
    "jpg", "jpeg", "png", "gif", "webp", "heic", "heif",
    "mp4", "mov", "m4v", "avi", "mkv", "webm"
)

def validate_album(name):
    if not isinstance(name, str) or not ALBUM_NAME.fullmatch(name):
        raise ValueError("Nome do álbum inválido.")
    if name in (".", "..") or name.endswith(" "):
        raise ValueError("Nome do álbum inválido.")
    return name

def photos_backend(remote, timeout=30):
    """Read public backend features only, never config/token output."""
    result = subprocess.run(
        ["rclone", "backend", "features", remote_path(remote)],
        capture_output=True, text=True, check=True, timeout=timeout)
    info = json.loads(result.stdout)
    if not isinstance(info, dict):
        raise ValueError("O rclone retornou recursos inválidos.")
    return str(info.get("Name", "")).strip().lower()

def eligible_paths(folder):
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise ValueError("A pasta local escolhida não existe.")
    suffixes = {"." + e for e in PHOTO_EXTENSIONS}
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*")
                  if path.is_file() and not path.is_symlink()
                  and path.suffix.lower() in suffixes)

def photos_copy_command(folder, remote, album="Drive para Linux"):
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("A pasta local escolhida não existe.")
    validate_album(album)
    dest = remote_path(remote, "album/" + album)
    cmd = ["rclone", "copy", str(root), dest, "--ignore-existing",
           "--transfers", "2", "--checkers", "2", "--retries", "2",
           "--stats", "1s"]
    # Case independent filters; all other files excluded.
    for extension in PHOTO_EXTENSIONS:
        cmd.extend(["--include", "*." + extension])
        cmd.extend(["--include", "*." + extension.upper()])
    return cmd

def upload_media(folder, remote, album="Drive para Linux", dry_run=True,
                 timeout=1800):
    candidates = eligible_paths(folder)
    if not candidates:
        return {"uploaded": 0, "candidates": 0, "state": "empty"}
    if photos_backend(remote) not in ("google photos", "googlephotos"):
        raise ValueError("Selecione um remoto do tipo Google Photos configurado no rclone.")
    cmd = photos_copy_command(folder, remote, album)
    if dry_run:
        return {"uploaded": 0, "candidates": len(candidates), "state": "preview"}
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=timeout)
    if result.returncode:
        raise RuntimeError("O Google Photos não confirmou a cópia; consulte os logs do rclone.")
    return {"uploaded": None, "candidates": len(candidates), "state": "submitted"}
