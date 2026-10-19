"""Resolve Drive file paths to safe, locally accessible Linux documents.

The desktop's default associated application (LibreOffice, OnlyOffice, etc.)
opens local copies or read-only FUSE paths. We do not impersonate Microsoft's
proprietary real-time presence, which is not part of rclone.
"""
from pathlib import Path
from mount_drive import mount_path
from sync_plan import validate_relative

def find_openable_file(relative, mirror_root, remote, online_root=None):
    validate_relative(relative)
    mirror = Path(mirror_root).expanduser().resolve()
    roots = [mirror]
    if online_root is not None and remote:
        roots.append(mount_path(remote, online_root))
    for root in roots:
        file = root / relative
        if (not file.is_symlink() and file.resolve().is_relative_to(root)
                and file.is_file()):
            return file
    return None
