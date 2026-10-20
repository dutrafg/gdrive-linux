"""Nonblocking per-profile lock shared by GUI and systemd synchronizer.

Reject lockfile symlinks and nonregular files before taking an advisory lock.
"""
import fcntl
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from background_sync import STATE_BASE, job_key


@contextmanager
def profile_transfer_lock(remote, folder, state_base=STATE_BASE):
    folder = Path(folder).expanduser().resolve()
    state_base = Path(state_base)
    # Do not follow a user-controlled symlink into an unexpected state directory.
    if state_base.is_symlink():
        raise ValueError("Diretório de sincronização simbólico não permitido.")
    state_base.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state_base.is_symlink() or not state_base.is_dir():
        raise ValueError("Diretório de sincronização inválido.")
    os.chmod(state_base, 0o700)
    lockfile = state_base / (job_key(remote, folder) + ".lock")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("Este sistema não oferece proteção para arquivos de trava.")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lockfile, flags, 0o600)
    except OSError as exc:
        raise ValueError("Arquivo de trava inseguro ou indisponível.") from exc
    try:
        identity = os.fstat(fd)
        if not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1:
            raise ValueError("Arquivo de trava não regular ou com múltiplos links.")
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(
                "A sincronização automática está trabalhando nesta conta. "
                "Aguarde sua conclusão antes da transferência manual.")
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
