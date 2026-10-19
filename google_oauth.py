"""Safe construction of rclone Google Drive OAuth configuration commands."""
import re
import subprocess

REMOTE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,49}$")
CLIENT_ID = re.compile(r"^[A-Za-z0-9._-]+\.apps\.googleusercontent\.com$")

def google_config_command(name, client_id=''):
    if not isinstance(name, str) or not REMOTE.fullmatch(name):
        raise ValueError("Nome da conta inválido (letras, números, _ ou -).")
    if not isinstance(client_id, str) or (client_id and not CLIENT_ID.fullmatch(client_id)):
        raise ValueError("Informe o ID OAuth de um aplicativo Desktop do Google.")
    command = ["rclone", "config", "create", name, "drive",
               "scope", "drive", "config_is_local", "true", "--no-output"]
    if client_id:
        command.extend(["client_id", client_id])
    return command

def verify_google_remote(name, timeout=45):
    """Check access to a configured remote without logging names or tokens."""
    if not isinstance(name, str) or not REMOTE.fullmatch(name):
        raise ValueError("Nome da conta inválido.")
    result = subprocess.run(["rclone", "lsd", name + ":"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=timeout, check=False)
    return result.returncode == 0
