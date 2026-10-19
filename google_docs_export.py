"""Read-only export of Google-native documents via rclone Drive formats.

Exports into a folder OUTSIDE the user's synced mirror. The original Google
Docs, Sheets and Slides remain unchanged. Also copies compatible Office files.
"""
import re
import subprocess
from pathlib import Path
from rclone_backend import remote_path
from rclone_errors import rclone_limits

FORMATS = {
    "office": "docx,xlsx,pptx,svg",
    "libreoffice": "odt,ods,odp,docx,xlsx,pptx,svg",
    "pdf": "pdf",
}
SUFFIXES = {
    "office": ("docx", "xlsx", "pptx"),
    "libreoffice": ("odt", "ods", "odp", "docx", "xlsx", "pptx"),
    "pdf": ("pdf",),
}

def export_folder(remote, home=None):
    remote_path(remote)
    base = Path(home).expanduser() if home else Path.home()
    docs = base / ("Documentos" if (base / "Documentos").is_dir() else "Documents")
    return docs / "DriveExports" / remote

def export_command(remote, destination, format_name="libreoffice", dry_run=False):
    remote_path(remote)
    if format_name not in FORMATS:
        raise ValueError("Formato de exportação desconhecido.")
    folder = Path(destination).expanduser().resolve()
    if folder == Path(folder.anchor):
        raise ValueError("Não é permitido exportar na raiz do sistema.")
    cmd = ["rclone", "copy", remote_path(remote), str(folder),
           "--drive-export-formats", FORMATS[format_name],
           "--ignore-existing", "--transfers", "1", "--checkers", "1",
           "--retries", "2"] + rclone_limits()
    for ext in SUFFIXES[format_name]:
        cmd.extend(["--include", "*." + ext])
    if dry_run:
        cmd.append("--dry-run")
    return cmd

def assert_not_inside_mirror(destination, mirror):
    dest = Path(destination).expanduser().resolve()
    current = Path(mirror).expanduser().resolve()
    if dest == current or dest in current.parents or current in dest.parents:
        raise ValueError("A exportação deve ocorrer fora da pasta de sincronização.")
    return dest

def export_documents(remote, mirror, format_name="libreoffice",
                     home=None, dry_run=False, timeout=1800):
    dest = assert_not_inside_mirror(export_folder(remote, home), mirror)
    # The Drive backend supports export_formats; other remotes don't.
    result = subprocess.run(["rclone", "backend", "features", remote_path(remote)],
                            capture_output=True, text=True, timeout=25)
    if result.returncode:
        raise RuntimeError("Não foi possível verificar o tipo da conta.")
    import json
    try:
        features = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise RuntimeError("Informação da conta inválida.")
    if not isinstance(features, dict) or str(features.get("Name", "")).lower() != "drive":
        raise ValueError("Escolha um remoto Google Drive para exportar documentos.")
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    command = export_command(remote, dest, format_name, dry_run)
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Exportação interrompida. Verifique cota Google e arquivos.")
    return {"directory": str(dest), "mode": format_name,
            "preview": dry_run, "completed": True}
