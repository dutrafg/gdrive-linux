"""Opt-in Google Drive streaming mount via rclone/FUSE and user systemd."""
import argparse
import os
import re
import shutil
from pathlib import Path

from settings import load_settings

SAFE_REMOTE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
MOUNT_ROOT = Path.home() / "DriveOnline"

def mount_path(remote, root=MOUNT_ROOT):
    if not isinstance(remote, str) or not SAFE_REMOTE.fullmatch(remote):
        raise ValueError("Nome de conta não aceito para montagem; renomeie no rclone.")
    base = Path(root).expanduser().resolve()
    return base / remote

def validate_mount(config, root=MOUNT_ROOT, require_tools=True, create=False):
    remote = config.get("account")
    mount = mount_path(remote, root)
    mirror_value = config.get("folder")
    if isinstance(mirror_value, str) and mirror_value:
        mirror = Path(mirror_value).expanduser().resolve()
        if (mount == mirror or mount in mirror.parents or mirror in mount.parents):
            raise ValueError("O disco virtual deve usar pasta separada da sincronização local.")
    if mount.is_symlink():
        raise ValueError("Montagem não aceita links simbólicos.")
    if mount.exists() and not mount.is_dir():
        raise ValueError("O ponto de montagem não é uma pasta.")
    if mount.exists() and not os.path.ismount(mount) and any(mount.iterdir()):
        raise ValueError("A pasta de montagem precisa estar vazia.")
    if require_tools:
        if not shutil.which("rclone"):
            raise RuntimeError("rclone não instalado.")
        if not shutil.which("fusermount3") and not shutil.which("fusermount"):
            raise RuntimeError("Instale o pacote fuse3 e habilite /dev/fuse.")
        if not Path("/dev/fuse").exists():
            raise RuntimeError("FUSE indisponível neste Linux (/dev/fuse ausente).")
    if create:
        mount.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not os.path.ismount(mount) and any(mount.iterdir()):
            raise ValueError("Pasta de montagem deixou de estar vazia.")
    return remote, mount

def command(config, root=MOUNT_ROOT, require_tools=False, create=False):
    remote, mount = validate_mount(config, root, require_tools, create)
    read_only = config.get("mount_read_only", True) is not False
    argv = ["rclone", "mount", remote + ":", str(mount),
            "--vfs-cache-mode", "full", "--vfs-cache-max-size", "2G",
            "--dir-cache-time", "5m", "--poll-interval", "1m"]
    if read_only:
        argv.append("--read-only")
    return argv

def main():
    parser = argparse.ArgumentParser(description="Montagem FUSE Drive para Linux")
    parser.add_argument("--serve", action="store_true",
                        help="Montar o remoto selecionado em modo foreground")
    parser.add_argument("--check", action="store_true",
                        help="Verificar requisitos sem montar")
    args = parser.parse_args()
    if not args.serve and not args.check:
        parser.error("Use --serve ou --check")
    try:
        cmd = command(load_settings(), require_tools=True, create=args.serve)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, "Drive para Linux: " + str(exc) + "\n")
    if args.check:
        print("Montagem disponível:", cmd[2])
        return 0
    os.execvp(cmd[0], cmd)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
