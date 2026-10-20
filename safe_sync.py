"""Non-destructive selective transfers; no delete or overwrite commands."""
import subprocess
from pathlib import Path
from rclone_errors import rclone_limits, friendly, is_rate_limit
from rclone_backend import remote_path
from sync_plan import validate_relative, conservative_plan, local_inventory, remote_inventory

def copyto_command(remote, folder, relative, direction):
    validate_relative(relative)
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Pasta local inexistente")
    target = root / relative
    if target.is_symlink() or any(p.is_symlink() for p in list(target.parents) if p != root and root in p.parents):
        raise ValueError("Caminho local simbólico não permitido")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Caminho fora da pasta local")
    cloud = remote_path(remote, relative)
    if direction == "upload":
        if not target.is_file() or target.is_symlink():
            raise ValueError("Arquivo local ausente")
        source, dest = str(target), cloud
    elif direction == "download":
        if target.exists() or target.is_symlink():
            raise ValueError("Destino local já existe")
        source, dest = cloud, str(target)
    else:
        raise ValueError("Direção inválida")
    # Ubuntu 22.04's rclone copyto --immutable can overwrite different
    # content. --ignore-existing preserves the destination on all supported
    # versions; background_sync confirms MD5 after each batch.
    return ["rclone", "copyto", source, dest,
            "--ignore-existing", "--retries", "2",
            "--transfers", "1", "--checkers", "1"] + rclone_limits()

def execute_additions(remote, folder, max_files=100, dry_run=True):
    """Re-scan before copying. Only unique paths; conflicts never touched."""
    local = local_inventory(folder)
    cloud = remote_inventory(remote)
    plan = conservative_plan(local, cloud)
    if len(plan.download) + len(plan.upload) > max_files:
        raise ValueError("Muitos arquivos novos; reduza o lote antes de executar")
    commands = [copyto_command(remote, folder, path, "download") for path in plan.download]
    commands += [copyto_command(remote, folder, path, "upload") for path in plan.upload]
    if dry_run:
        return plan, 0
    completed = 0
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        if result.returncode:
            raise RuntimeError(("Transferência interrompida após " + str(completed) +
                                " arquivos. " + friendly(result.stderr)) if
                               is_rate_limit(result.stderr) else
                               "Transferência interrompida; confira a conta e tente mais tarde.")
        completed += 1
    return plan, completed
