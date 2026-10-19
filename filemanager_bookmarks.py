"""Add or remove an rclone FUSE mount from GTK/Nautilus file manager bookmarks.

Works in Zorin Files, Nautilus and other GTK bookmark consumers.
Preserves unrelated bookmarks; never deletes or modifies cloud files.
"""
import os
import tempfile
from pathlib import Path

from mount_drive import mount_path

def bookmark_file(home=None):
    home = Path(home) if home else Path.home()
    return home / ".config" / "gtk-3.0" / "bookmarks"

def bookmark_entry(remote, root=None):
    path = mount_path(remote, root) if root is not None else mount_path(remote)
    return path.as_uri() + " Drive - " + remote

def set_bookmark(remote, enable, file=None, root=None):
    if type(enable) is not bool:
        raise ValueError("Ação inválida.")
    path = Path(file) if file else bookmark_file()
    uri = bookmark_entry(remote, root).split(" ", 1)[0]
    try:
        current = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        current = []
    # Preserve all user bookmarks, replacing only the URI managed here.
    kept = [line for line in current if line.split(" ", 1)[0] != uri]
    if enable:
        kept.append(bookmark_entry(remote, root))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".bookmarks-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write("\n".join(kept) + ("\n" if kept else ""))
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return bool(enable)
