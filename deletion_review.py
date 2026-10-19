"""Explicit, recoverable deletion resolution.

Users must select each deletion. The remaining copy is archived, not erased.
The background service does not propagate deletions without that action.
"""
import fcntl
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from background_sync import (BACKUP_BASE, STATE_BASE, fingerprint, inventories,
                             job_key, read_baseline, safe_local_target, local_md5,
                             save_private_json)
from rclone_backend import list_remotes, remote_path
from sync_plan import validate_relative
from sync_filters import filtered_inventory, parse_rules
from settings import load_settings


def selected_rules(remote, folder, configuration=None):
    """Manual review must honor the same selected folders as auto sync."""
    options = load_settings() if configuration is None else configuration
    configured = options.get("sync_profiles", [])
    for profile in configured:
        if (profile.get("account") == remote and
                Path(profile.get("folder", "")).expanduser().resolve() == folder):
            return (parse_rules(profile.get("sync_includes", [])),
                    parse_rules(profile.get("sync_excludes", [])))
    if configured:
        # Do not review a different account with another profile's history.
        raise ValueError("A conta e a pasta não correspondem a um perfil ativo.")
    if (options.get("account") == remote and
            Path(options.get("folder", "")).expanduser().resolve() == folder):
        return (parse_rules(options.get("sync_includes", [])),
                parse_rules(options.get("sync_excludes", [])))
    return [], []

def find_deletions(local, cloud, baseline):
    candidates = []
    for name in sorted(set(baseline)):
        validate_relative(name)
        if name in local and name not in cloud:
            if fingerprint(local[name]) == baseline[name]:
                candidates.append((name, "cloud"))
        elif name in cloud and name not in local:
            if fingerprint(cloud[name]) == baseline[name]:
                candidates.append((name, "local"))
    return candidates


def load_candidates(remote, folder, state_base=STATE_BASE):
    base = Path(folder).expanduser().resolve()
    baseline = read_baseline(state_base / (job_key(remote, base) + ".json"))
    includes, excludes = selected_rules(remote, base)
    local, cloud = inventories(remote, base, includes, excludes)
    baseline = filtered_inventory(baseline, includes, excludes)
    return find_deletions(local, cloud, baseline)


def archive_deletion(remote, folder, relative, missing_side,
                     state_base=STATE_BASE, backup_base=BACKUP_BASE):
    """Archive the copy on the survivor side with a fresh plan under a lock."""
    validate_relative(relative)
    if missing_side not in ("local", "cloud"):
        raise ValueError("Origem da exclusão inválida.")
    remote_path(remote)
    if remote not in list_remotes():
        raise ValueError("Conta não configurada no rclone.")
    base = Path(folder).expanduser().resolve()
    if not base.is_dir():
        raise ValueError("Pasta local indisponível.")
    state_base.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = job_key(remote, base)
    with (state_base / (key + ".lock")).open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Aguarde o ciclo de sincronização atual.")
        snapshot_path = state_base / (key + ".json")
        baseline = read_baseline(snapshot_path)
        includes, excludes = selected_rules(remote, base)
        local, cloud = inventories(remote, base, includes, excludes)
        visible_baseline = filtered_inventory(baseline, includes, excludes)
        if (relative, missing_side) not in find_deletions(local, cloud, visible_baseline):
            raise ValueError("A exclusão mudou desde a análise; examine novamente.")
        run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10]
        if missing_side == "cloud":
            source = safe_local_target(base, relative)
            if not source.is_file() or local_md5(source) != visible_baseline[relative]:
                raise ValueError("O arquivo mudou antes de arquivar; operação cancelada.")
            archive_root = Path(backup_base).expanduser().resolve() / key / "deleted" / run
            destination = archive_root / relative
            if not destination.resolve().is_relative_to(archive_root):
                raise ValueError("Destino de arquivamento inválido.")
            destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            shutil.move(str(source), str(destination))
            archived = str(destination)
        else:
            # Not permanent delete: move the remote item into a reserved archive.
            source = remote_path(remote, relative)
            dest = remote_path(remote, ".gdrive-linux-history/archived-deletions/" + run + "/" + relative)
            response = subprocess.run(
                ["rclone", "moveto", source, dest],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
            if response.returncode:
                raise RuntimeError("Não foi possível arquivar a cópia remota.")
            archived = dest
        baseline.pop(relative, None)
        save_private_json(snapshot_path, {"md5": baseline})
        return archived
