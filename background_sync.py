"""Safe, incremental, bidirectional mirror job powered by rclone.

Requires an explicitly enabled user timer. Does not propagate deletions.
A last-known-good MD5 baseline distinguishes one-sided edits from conflicts.
"""
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rclone_backend import list_remotes, remote_path
from settings import load_settings
from sync_plan import local_inventory, remote_inventory, validate_relative

STATE_BASE = Path.home() / ".local" / "state" / "gdrive-linux"
BACKUP_BASE = Path.home() / ".local" / "share" / "gdrive-linux" / "backups"
EXCLUDED = (".gdrive-linux-history", ".gdrive-linux-backups")
MAX_FILES = 100

def is_private_path(relative):
    return relative.split("/", 1)[0] in EXCLUDED

def fingerprint(value):
    return value[1].lower() if isinstance(value, (list, tuple)) and len(value) == 2 and value[0].lower() == "md5" else None

def build_plan(local, cloud, baseline):
    """Return (actions, conflicts). Never delete or overwrite both-edited paths."""
    actions, conflicts = [], []
    for path in sorted(set(local) | set(cloud)):
        validate_relative(path)
        if is_private_path(path):
            continue
        local_md5 = fingerprint(local.get(path))
        remote_md5 = fingerprint(cloud.get(path))
        old = baseline.get(path)
        if path in local and path in cloud:
            if local_md5 is not None and local_md5 == remote_md5:
                continue
            if old and local_md5 and remote_md5:
                if remote_md5 == old and local_md5 != old:
                    actions.append(("upload_update", path))
                    continue
                if local_md5 == old and remote_md5 != old:
                    actions.append(("download_update", path))
                    continue
            conflicts.append(path)
        elif old is not None:
            # Prior presence means a deletion or unavailable file; never resurrect blindly.
            conflicts.append(path)
        elif path in local:
            actions.append(("upload_new", path))
        else:
            actions.append(("download_new", path))
    return actions, conflicts

def safe_local_target(root, relative):
    validate_relative(relative)
    root = root.resolve()
    target = root / relative
    if not target.resolve().is_relative_to(root):
        raise ValueError("Caminho fora da pasta de sincronização")
    ancestor = target
    while ancestor != root:
        if ancestor.is_symlink():
            raise ValueError("Links simbólicos não podem ser sincronizados")
        ancestor = ancestor.parent
    return target

def job_key(remote, folder):
    return hashlib.sha256((remote + "\0" + str(folder.resolve())).encode()).hexdigest()[:24]

def save_private_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                       "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

def read_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def inventories(remote, folder):
    local = {key: val for key, val in local_inventory(folder).items()
             if not is_private_path(key)}
    cloud = {key: val for key, val in remote_inventory(remote).items()
             if not is_private_path(key)}
    return local, cloud

def transfer_one(remote, folder, operation, relative, run_id, backup_base=BACKUP_BASE):
    """One rclone copy. For modified files the old destination is backed up."""
    target = safe_local_target(folder, relative)
    cloud = remote_path(remote, relative)
    uploading = operation.startswith("upload")
    if uploading and not target.is_file():
        raise ValueError("Arquivo local não encontrado")
    if not uploading and operation.endswith("new") and (target.exists() or target.is_symlink()):
        raise ValueError("Destino local já existe")
    src, dst = (str(target), cloud) if uploading else (cloud, str(target))
    command = ["rclone", "copyto", src, dst, "--retries", "2"]
    if operation.endswith("new"):
        command.append("--ignore-existing")
    else:
        if uploading:
            backup = remote_path(remote, ".gdrive-linux-history/" + run_id)
        else:
            backup = str(backup_base / job_key(remote, folder) / run_id)
            Path(backup).mkdir(parents=True, mode=0o700, exist_ok=True)
        command.extend(["--backup-dir", backup])
    result = subprocess.run(command, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=900)
    if result.returncode:
        raise RuntimeError("Falha ao copiar arquivo: " + relative)

def refresh_baseline(previous, local, cloud):
    """Commit only verified identical pairs; keep older baseline for conflicts."""
    result = dict(previous)
    for path in set(local) & set(cloud):
        local_md5, remote_md5 = fingerprint(local[path]), fingerprint(cloud[path])
        if local_md5 and local_md5 == remote_md5 and not is_private_path(path):
            result[path] = local_md5
    for path in set(previous) - (set(local) | set(cloud)):
        del result[path]
    return result

def run_once(config=None, state_base=STATE_BASE, backup_base=BACKUP_BASE,
             max_files=MAX_FILES, dry_run=False):
    config = load_settings() if config is None else config
    if not config.get("auto_sync_enabled", False):
        return {"state": "disabled", "copied": 0, "conflicts": 0}
    remote = config.get("account")
    folder_value = config.get("folder")
    if not isinstance(remote, str) or not remote or not isinstance(folder_value, str):
        raise ValueError("Selecione uma conta e pasta nas configurações")
    folder = Path(folder_value).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError("A pasta escolhida está indisponível; nenhuma ação executada")
    if remote not in list_remotes():
        raise ValueError("Conta rclone não disponível")
    state_base.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(state_base, 0o700)
    key = job_key(remote, folder)
    with (state_base / (key + ".lock")).open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"state": "busy", "copied": 0, "conflicts": 0}
        snapshot_path = state_base / (key + ".json")
        baseline = read_json(snapshot_path).get("md5", {})
        if not isinstance(baseline, dict):
            raise ValueError("Estado da sincronização inválido")
        local, cloud = inventories(remote, folder)
        actions, conflicts = build_plan(local, cloud, baseline)
        if dry_run:
            return {"state": "preview", "copied": 0,
                    "conflicts": len(conflicts), "pending": len(actions)}
        if len(actions) > max_files:
            # Bounded batch, so frequent scans never overload Google Drive.
            actions = actions[:max_files]
        copied = 0
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        try:
            for operation, relative in actions:
                # No deletion. If an old target was modified concurrently,
                # destination backup keeps the former copy recoverable.
                transfer_one(remote, folder, operation, relative, run_id, backup_base)
                copied += 1
        finally:
            # Keep track of copies actually verified even if a later copy fails.
            local_after, cloud_after = inventories(remote, folder)
            new_base = refresh_baseline(baseline, local_after, cloud_after)
            save_private_json(snapshot_path, {"md5": new_base})
        status = {"state": "ok" if not conflicts else "conflicts",
                  "copied": copied, "conflicts": len(conflicts),
                  "pending": max(0, len(actions) - copied),
                  "time": datetime.now(timezone.utc).isoformat()}
        save_private_json(state_base / "latest.json", status)
        return status

def main():
    parser = argparse.ArgumentParser(description="Sincronização segura do Drive para Linux")
    parser.add_argument("--once", action="store_true", help="Executar uma verificação")
    parser.add_argument("--dry-run", action="store_true", help="Não transferir arquivos")
    args = parser.parse_args()
    if not args.once and not args.dry_run:
        parser.error("Use --once ou --dry-run")
    try:
        status = run_once(dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        status = {"state": "error", "message": str(exc),
                  "time": datetime.now(timezone.utc).isoformat()}
        save_private_json(STATE_BASE / "latest.json", status)
        print("Drive para Linux: verificação interrompida.", file=sys.stderr)
        return 1
    print(json.dumps(status, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
