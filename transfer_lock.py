"""Non-blocking per-profile lock shared with the systemd synchronizer.

Prevents a manual rclone copy from racing with an automatic service cycle.
"""
import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from background_sync import STATE_BASE, job_key

@contextmanager
def profile_transfer_lock(remote, folder, state_base=STATE_BASE):
    folder = Path(folder).expanduser().resolve()
    state_base = Path(state_base)
    state_base.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(state_base, 0o700)
    lockfile = state_base / (job_key(remote, folder) + ".lock")
    with lockfile.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(
                "A sincronização automática está trabalhando nesta conta. "
                "Aguarde sua conclusão antes da transferência manual.")
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
