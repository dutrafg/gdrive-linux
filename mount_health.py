"""Read-only, privacy-preserving status of the user's rclone mount service.

Never show unfiltered journal lines: logs can include file names, remote URLs,
credentials, and other personal information.
"""
import os
import subprocess
from pathlib import Path

SERVICE = "gdrive-linux-mount.service"

def command_output(args, timeout=8):
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, result.stdout or "", result.stderr or ""
    except (OSError, subprocess.SubprocessError):
        return 1, "", ""

def classify_mount_error(logs):
    """Return an actionable fixed message, not sensitive unfiltered logs."""
    lower = (logs or "").lower()
    if any(term in lower for term in ("rate_limit_exceeded", "ratelimitexceeded",
        "userqueriesperminuteperproject", "quota exceeded", "quota_exceeded")):
        return ("O Google recusou a montagem por limite de requisições (403). "
                "Configure um Client ID/Secret próprio no rclone e aguarde a cota.")
    if any(term in lower for term in ("fuse: permission denied", "fusermount3: mount failed: permission denied",
                                      "failed to open /dev/fuse", "fuse device not found",
                                      "fusermount: exit status 1", "operation not permitted")):
        return ("O Linux bloqueou a montagem FUSE. Confira /dev/fuse, fuse3 "
                "e as permissões/AppArmor do Zorin OS.")
    if "conta ausente no rclone" in lower or "didn't find section in config file" in lower:
        return ("A conta selecionada não existe no rclone usado pelo serviço. "
                "Abra Contas, verifique o remoto e confira o arquivo rclone.conf.")
    if ("pasta online pertence a outro usuário" in lower or
            "sem permissão de escrita na pasta de montagem" in lower):
        return ("A pasta da unidade virtual tem proprietário/permissões incorretos. "
                "Ajuste apenas ~/DriveOnline/<conta>, sem modificar arquivos do Drive.")
    if ("failed to connect to bus" in lower or "no medium found" in lower):
        return ("systemd de usuário não está acessível. Entre na sessão gráfica "
                "normal do Zorin antes de iniciar a montagem.")
    if ("snap" in lower and ("permission denied" in lower or "not allowed" in lower)):
        return ("A instalação Snap do rclone pode impedir acesso ao FUSE. "
                "Utilize uma instalação de rclone compatível com FUSE no Linux.")
    if "directory is not empty" in lower or "mountpoint is not empty" in lower:
        return ("A pasta de montagem contém arquivos; escolha uma pasta vazia "
                "antes de tentar montar novamente.")
    if "transport endpoint is not connected" in lower:
        return ("A montagem FUSE ficou desconectada. Feche arquivos abertos, "
                "desmonte a unidade e tente montar novamente.")
    if any(term in lower for term in ("flag provided but not defined", "unknown flag",
                                      "unknown shorthand flag")):
        return ("A versão do rclone não aceita uma opção usada na montagem. "
                "Atualize o rclone pela distribuição oficial.")
    if any(term in lower for term in ("invalid_grant", "invalid credentials",
                                      "unauthorized", "token expired", "oauth")):
        return ("A autenticação Google falhou. Reautorize a conta no rclone "
                "usando suas credenciais OAuth.")
    if "couldn't find root directory" in lower or "failed to create file system" in lower:
        return ("O rclone não conseguiu consultar o Google Drive. Verifique a conta, "
                "a conexão e a cota da API.")
    if "fusermount" in lower and ("not found" in lower or "no such file" in lower):
        return ("O comando fusermount não está disponível. Instale fuse3 "
                "e verifique o PATH do serviço.")
    if (("rclone" in lower and ("not found" in lower or "no such file" in lower))
            or "rclone não encontrado no path" in lower):

        return "rclone não disponível para o serviço systemd. Verifique a instalação."
    return ("O serviço não concluiu a montagem. Abra Configurações → Diagnóstico "
            "ou consulte o status do serviço com systemctl --user status " + SERVICE + ".")

def service_state():
    """Return active/inactive/failed/activating/unknown without leaking output."""
    code, stdout, _ = command_output(
        ["systemctl", "--user", "show", SERVICE,
         "--property=ActiveState", "--value"])
    if code != 0:
        return "unknown"
    state = stdout.strip().splitlines()[0] if stdout.strip() else "unknown"
    return state if state in ("active", "inactive", "failed", "activating",
                              "deactivating", "reloading") else "unknown"

def service_journal():
    """Recent log lines are handled privately and never displayed as-is."""
    code, stdout, _ = command_output(
        ["journalctl", "--user", "--unit", SERVICE, "--no-pager",
         "--lines", "25", "--output", "cat"], timeout=10)
    return stdout if code == 0 else ""

def mount_diagnosis(path, state=None, journal=None):
    """Give distinct ready/startup/failed states; never claim a mount from systemd alone."""
    mounted = mount_ready(path)
    if mounted:
        return "Disco virtual montado. Você pode abri-lo no gerenciador de arquivos."
    state = state if state is not None else service_state()
    if state == "activating":
        return "O serviço está iniciando; aguarde o rclone preparar a montagem FUSE."
    if state == "active":
        details = classify_mount_error(journal if journal is not None else service_journal())
        return ("O serviço está ativo, mas o disco ainda NÃO está montado. " + details)
    if state in ("failed", "inactive"):
        return classify_mount_error(journal if journal is not None else service_journal())
    return ("Não foi possível verificar o serviço de montagem. "
            "Abra o diagnóstico em Configurações.")

def mount_ready(path):
    try:
        return Path(path).is_mount()
    except OSError:
        return False
