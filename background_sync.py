"""Safe, incremental, bidirectional mirror job powered by rclone.

Requires an explicitly enabled user timer. Does not propagate deletions.
A last-known-good MD5 baseline distinguishes one-sided edits from conflicts.
"""
import argparse
import fcntl
import hashlib
import json
import re
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rclone_backend import list_remotes, remote_path
from settings import load_settings
from rclone_config import activate_worker_config
from sync_plan import local_inventory, remote_inventory, validate_relative
from sync_filters import filtered_inventory, parse_rules
from sync_profiles import effective_profiles, get_profile_mode, ensure_external_volume_present
from rclone_errors import (rclone_limits, is_rate_limit, friendly,
                           cooldown_active, quota_retry_after)

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
        elif path in cloud and remote_md5 is None:
            # Google-native Docs and some provider files do not have a
            # comparable MD5. Repeated copyto fails or exports ambiguous
            # formats; leave these for the explicit Documents export flow.
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

def local_md5(path):
    """Recheck the surviving file just before any opt-in local archiving."""
    digest = hashlib.md5()
    with Path(path).open("rb") as source:
        while True:
            data = source.read(1024 * 1024)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()

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

def read_transfer_checkpoint(path):
    """Read informational in-flight progress; NEVER use it to authorize overwrites.

    Each new cycle re-inventories local and cloud; this only explains what
    rclone reported successful before a crash or a disconnected Drive.
    """
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return {}
    if path.is_symlink() or not path.is_file():
        raise ValueError("Registro de retomada inseguro; link simbólico recusado.")
    info = read_json(path)
    count = info.get("planned")
    completed = info.get("completed")
    if (info.get("version") != 1 or type(count) is not int
            or not 0 <= count <= MAX_FILES * 100
            or not isinstance(completed, list) or len(completed) > count):
        raise ValueError("Registro de retomada danificado; os arquivos não serão alterados com base nele.")
    for row in completed:
        if not isinstance(row, dict) or row.get("operation") not in (
                "upload_new", "download_new", "upload_update", "download_update"):
            raise ValueError("Registro de retomada contém operação inválida.")
        validate_relative(row.get("path"))
    return info


def read_baseline(path):
    """Fail closed on an existing damaged history; never resurrect deleted files.

    A truly new profile has no snapshot. An existing but invalid snapshot
    requires recovery, not treating everything as never synchronized.
    """
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return {}
    if path.is_symlink() or not path.is_file():
        raise ValueError("Histórico de sincronização inseguro; arquivo não é regular.")
    data = read_json(path)
    hashes = data.get("md5")
    if not isinstance(hashes, dict):
        raise ValueError("Histórico de sincronização ilegível. Faça backup e restaure "
                         "o histórico antes de sincronizar; nenhum dado foi alterado.")
    for relative, digest in hashes.items():
        validate_relative(relative)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{32}", digest):
            raise ValueError("Histórico de sincronização contém hashes inválidos; "
                             "a cópia foi interrompida por segurança.")
    return hashes

def inventories(remote, folder, includes=(), excludes=()):
    local = {key: val for key, val in local_inventory(folder).items()
             if not is_private_path(key)}
    cloud = {key: val for key, val in remote_inventory(remote).items()
             if not is_private_path(key)}
    return (filtered_inventory(local, includes, excludes),
            filtered_inventory(cloud, includes, excludes))

def transfer_one(remote, folder, operation, relative, run_id, backup_base=BACKUP_BASE,
                 expected_local_md5=None):
    """One rclone copy. For modified files the old destination is backed up."""
    target = safe_local_target(folder, relative)
    cloud = remote_path(remote, relative)
    uploading = operation.startswith("upload")
    if uploading and not target.is_file():
        raise ValueError("Arquivo local não encontrado")
    # Re-read local content immediately before the transfer. A file edited by
    # the user since the inventory cannot be uploaded/overwritten silently.
    # This is especially important while the user saves from LibreOffice.
    if expected_local_md5 is not None:
        if (not target.is_file() or target.is_symlink()
                or local_md5(target) != expected_local_md5):
            raise RuntimeError("Arquivo local mudou durante a sincronização; "
                               "a transferência foi suspensa para protegê-lo.")
    if not uploading and operation.endswith("new") and (target.exists() or target.is_symlink()):
        raise ValueError("Destino local já existe")
    src, dst = (str(target), cloud) if uploading else (cloud, str(target))
    command = ["rclone", "copyto", src, dst, "--retries", "2",
               "--transfers", "1", "--checkers", "1"] + rclone_limits()
    if operation.endswith("new"):
        # Unlike --ignore-existing, --immutable reports a concurrent remote
        # collision instead of silently claiming a newly uploaded file is safe.
        # Local downloads remain non-overwriting.
        command.append("--immutable" if uploading else "--ignore-existing")
    else:
        if uploading:
            backup = remote_path(remote, ".gdrive-linux-history/" + run_id)
        else:
            backup = str(backup_base / job_key(remote, folder) / run_id)
            Path(backup).mkdir(parents=True, mode=0o700, exist_ok=True)
        command.extend(["--backup-dir", backup])
    result = subprocess.run(command, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=True, timeout=900)
    if result.returncode:
        if is_rate_limit(result.stderr):
            raise RuntimeError(friendly(result.stderr))
        raise RuntimeError("Falha de acesso ou escrita durante a transferência: " + relative)

def archive_unilateral_deletions(remote, folder, local, cloud, baseline,
                                 run_id, backup_base=BACKUP_BASE, max_items=20):
    """Opt-in reconciliation: move unchanged surviving copies into recoverable archives.

    The caller holds the job lock. It never permanently deletes a file.
    Both-edited files and paths without a verified MD5 stay conflicted.
    """
    archived = []
    for relative in sorted(set(baseline)):
        if len(archived) >= max_items:
            break
        if is_private_path(relative):
            continue
        old = baseline[relative]
        local_still = relative in local
        cloud_still = relative in cloud
        if local_still == cloud_still:
            continue
        if local_still:
            if fingerprint(local[relative]) != old:
                continue
            target = safe_local_target(folder, relative)
            if not target.is_file() or local_md5(target) != old:
                # The user edited this file since the previous inventory.
                # Never move the freshly edited copy out of their workspace.
                continue
            archive_root = backup_base / job_key(remote, folder) / "deleted" / run_id
            archive = archive_root / relative
            archive.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if archive.exists():
                raise RuntimeError("Arquivo de recuperação já existe.")
            shutil.move(str(target), str(archive))
        else:
            if fingerprint(cloud[relative]) != old:
                continue
            src = remote_path(remote, relative)
            dst = remote_path(remote,
                ".gdrive-linux-history/archived-deletions/" + run_id + "/" + relative)
            done = subprocess.run(["rclone", "moveto", src, dst] + rclone_limits(),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  text=True, timeout=900)
            if done.returncode:
                if is_rate_limit(done.stderr):
                    raise RuntimeError(friendly(done.stderr))
                raise RuntimeError("Falha ao arquivar arquivo remoto; nada foi apagado permanentemente.")
        archived.append(relative)
    return archived

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
    activate_worker_config(config)
    if not config.get("auto_sync_enabled", False):
        return {"state": "disabled", "copied": 0, "conflicts": 0}
    mode = get_profile_mode(config)
    includes = parse_rules(config.get("sync_includes", []))
    excludes = parse_rules(config.get("sync_excludes", []))
    remote = config.get("account")
    folder_value = config.get("folder")
    if not isinstance(remote, str) or not remote or not isinstance(folder_value, str):
        raise ValueError("Selecione uma conta e pasta nas configurações")
    folder = Path(folder_value).expanduser().resolve()
    home = Path.home().resolve()
    if (folder == home or folder in home.parents
            or STATE_BASE.resolve().is_relative_to(folder)
            or BACKUP_BASE.resolve().is_relative_to(folder)):
        raise ValueError("Escolha uma subpasta exclusiva para o Drive; "
                         "não sincronize a pasta pessoal inteira ou pastas de backup.")
    if not folder.is_dir():
        raise ValueError("A pasta escolhida está indisponível; nenhuma ação executada")
    ensure_external_volume_present(folder)
    if remote not in list_remotes():
        raise ValueError("Conta rclone não disponível")
    state_base.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(state_base, 0o700)
    key = job_key(remote, folder)
    latest_path = state_base / (key + "-latest.json")
    latest_status = read_json(latest_path)
    if cooldown_active(latest_status):
        return latest_status
    with (state_base / (key + ".lock")).open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"state": "busy", "copied": 0, "conflicts": 0}
        snapshot_path = state_base / (key + ".json")
        full_baseline = read_baseline(snapshot_path)
        baseline = filtered_inventory(full_baseline, includes, excludes)
        excluded_baseline = {p: digest for p, digest in full_baseline.items()
                             if p not in baseline}
        local, cloud = inventories(remote, folder, includes, excludes)
        actions, conflicts = build_plan(local, cloud, baseline)
        actions_before_direction = len(actions)
        if mode == "upload":
            actions = [item for item in actions if item[0].startswith("upload")]
        elif mode == "download":
            actions = [item for item in actions if item[0].startswith("download")]
        skipped_direction = actions_before_direction - len(actions)
        if dry_run:
            return {"state": "preview", "copied": 0,
                    "conflicts": len(conflicts), "pending": len(actions),
                    "skipped_direction": skipped_direction}
        planned_count = len(actions)
        if len(actions) > max_files:
            # Gradual batches; never require manually reducing the batch.
            actions = actions[:max_files]
        copied = 0
        archived = []
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        original_error = None
        checkpoint_path = state_base / (key + "-inflight.json")
        completed_operations = []
        checkpoint = {
            "version": 1, "planned": planned_count,
            "completed": completed_operations,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        # Write-ahead progress is advisory, not a replacement for checking
        # destination MD5s and refreshing the last-known-good baseline.
        save_private_json(checkpoint_path, checkpoint)
        try:
            if mode == "bidirectional" and config.get("auto_archive_deletions") is True:
                archived = archive_unilateral_deletions(remote, folder, local, cloud,
                                                       baseline, run_id, backup_base)
                for relative in archived:
                    baseline.pop(relative, None)
                conflicts = [path for path in conflicts if path not in archived]
            for operation, relative in actions:
                # Destination backups protect one-sided updates. A failed copy
                # must not be hidden by a later network error while rescanning.
                expected = fingerprint(local.get(relative))
                transfer_one(remote, folder, operation, relative, run_id, backup_base,
                             expected_local_md5=expected)
                copied += 1
                completed_operations.append({"operation": operation, "path": relative})
                save_private_json(checkpoint_path, checkpoint)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            original_error = exc
        try:
            # Preserve independently verified completed copies, but never
            # replace the original failure with an unrelated re-scan failure.
            local_after, cloud_after = inventories(remote, folder, includes, excludes)
            new_base = refresh_baseline(baseline, local_after, cloud_after)
            save_private_json(snapshot_path, {"md5": dict(excluded_baseline, **new_base)})
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            if original_error is None:
                raise
        if original_error is not None:
            raise original_error
        # Only clear the advisory journal AFTER both inventories and baseline
        # commit succeed; an interrupted cycle leaves evidence for diagnostics.
        checkpoint_path.unlink(missing_ok=True)
        remaining = max(0, planned_count - copied)
        status = {"state": ("conflicts" if conflicts else
                            "partial" if remaining else "ok"),
                  "copied": copied, "archived": len(archived),
                  "conflicts": len(conflicts), "pending": remaining,
                  "skipped_direction": skipped_direction,
                  "time": datetime.now(timezone.utc).isoformat()}
        status["account"] = remote
        status["folder"] = str(folder)
        status["mode"] = mode
        save_private_json(latest_path, status)
        save_private_json(state_base / "latest.json", status)
        return status

def notify_if_changed(previous, current):
    """Desktop notification only when a new error/conflict condition appears."""
    state = current.get("state")
    if state not in ("conflicts", "error", "quota"):
        return False
    if previous.get("state") == state and (
        state == "error" or previous.get("conflicts") == current.get("conflicts")):
        return False
    if not shutil.which("notify-send"):
        return False
    message = ("Conflitos pendentes; verifique o Drive para Linux."
               if state == "conflicts" else
               "API do Google temporariamente limitada. Confira Client ID próprio no rclone." if state == "quota" else
               "Falha de sincronização. Verifique a conta e a pasta local.")
    try:
        subprocess.run(["notify-send", "--app-name=Drive para Linux",
                        "Drive para Linux", message], timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return False
    return True

def run_profiles(config=None, state_base=STATE_BASE, backup_base=BACKUP_BASE,
                 max_files=MAX_FILES, dry_run=False):
    """Run multiple account+folder pairs independently, preserving errors."""
    config = load_settings() if config is None else config
    activate_worker_config(config)
    jobs = effective_profiles(config)
    if not jobs:
        return {"state": "disabled", "copied": 0, "pending": 0,
                "conflicts": 0, "profiles": []}
    results = []
    for profile in jobs:
        if not profile.get("enabled", True):
            continue
        try:
            status = run_once(dict(profile, auto_sync_enabled=True),
                              state_base, backup_base,
                              max_files=max_files, dry_run=dry_run)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            raw = str(exc) + " " + str(getattr(exc, "stderr", "") or "")
            quota = is_rate_limit(raw)
            checkpoint_path = state_base / (
                job_key(profile["account"], Path(profile["folder"])) + "-inflight.json")
            try:
                progress = read_transfer_checkpoint(checkpoint_path)
            except (OSError, ValueError):
                progress = {}
            completed_count = len(progress.get("completed", []))
            pending_count = max(0, progress.get("planned", 0) - completed_count)
            status = {"state": "quota" if quota else "error",
                      "message": friendly(raw) if quota else str(exc)[:300],
                      "copied": 0, "conflicts": 0, "pending": pending_count,
                      "unverified_transfers": completed_count,
                      "account": profile["account"], "folder": profile["folder"],
                      "time": datetime.now(timezone.utc).isoformat()}
            if quota:
                status["retry_after"] = quota_retry_after()
            key = job_key(profile["account"], Path(profile["folder"]))
            save_private_json(state_base / (key + "-latest.json"), status)
        results.append(status)
    if not results:
        return {"state": "disabled", "copied": 0, "pending": 0,
                "conflicts": 0, "profiles": []}
    states = {x.get("state") for x in results}
    state = ("quota" if "quota" in states else "error" if "error" in states
             else "conflicts" if "conflicts" in states
             else "partial" if "partial" in states
             else "busy" if "busy" in states
             else "preview" if dry_run else "ok")
    aggregate = {
        "state": state, "copied": sum(x.get("copied", 0) for x in results),
        "pending": sum(x.get("pending", 0) for x in results),
        "conflicts": sum(x.get("conflicts", 0) for x in results),
        "archived": sum(x.get("archived", 0) for x in results),
        "skipped_direction": sum(x.get("skipped_direction", 0) for x in results),
        "profiles": results,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    if not dry_run:
        save_private_json(state_base / "latest.json", aggregate)
    return aggregate

def main():
    parser = argparse.ArgumentParser(description="Sincronização segura do Drive para Linux")
    parser.add_argument("--once", action="store_true", help="Executar uma verificação")
    parser.add_argument("--dry-run", action="store_true", help="Não transferir arquivos")
    args = parser.parse_args()
    if not args.once and not args.dry_run:
        parser.error("Use --once ou --dry-run")
    previous = read_json(STATE_BASE / "latest.json")
    try:
        status = run_profiles(dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raw = str(exc) + " " + str(getattr(exc, "stderr", "") or "")
        quota = is_rate_limit(raw)
        status = {"state": "quota" if quota else "error",
                  "message": friendly(raw) if quota else str(exc)[:400],
                  "time": datetime.now(timezone.utc).isoformat()}
        if quota:
            status["retry_after"] = quota_retry_after()
        save_private_json(STATE_BASE / "latest.json", status)
        notify_if_changed(previous, status)
        print("Drive para Linux: verificação interrompida.", file=sys.stderr)
        return 1
    if not args.dry_run:
        notify_if_changed(previous, status)
    print(json.dumps(status, ensure_ascii=False))
    # Let systemd distinguish an actually failed cycle from a successful
    # process invocation. Pending batches and conflicts are recoverable states.
    return 1 if status.get("state") in ("error", "quota") else 0

if __name__ == "__main__":
    raise SystemExit(main())
