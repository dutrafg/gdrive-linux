"""Read-only mount preflight for Zorin OS and other Linux desktops.

No Google API call, no token inspection, no modifications to folders.
The GUI presents only fixed troubleshooting guidance, never raw rclone.conf.
"""
import os
import shutil
import subprocess
from pathlib import Path

from mount_drive import mount_path, validate_mount, MOUNT_ROOT
from mount_health import mount_ready
from rclone_backend import list_remotes


def _command_ready(argv, timeout=10):
    try:
        result = subprocess.run(
            argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=timeout, check=False)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def inspect_mount(config, root=MOUNT_ROOT):
    """Return a diagnostic summary using local operating-system data only."""
    results = []
    def check(name, passed, guidance):
        results.append({"name": name, "ok": bool(passed), "detail": guidance})

    remote = config.get("account")
    selected = bool(isinstance(remote, str) and remote)
    check("Conta selecionada", selected,
          "Selecione uma conta Google na página Contas." if not selected
          else "Conta selecionada no aplicativo.")

    rclone = shutil.which("rclone")
    check("Executável rclone", bool(rclone),
          "Instale o rclone e confirme que está disponível em /usr/bin ou /usr/local/bin."
          if not rclone else "rclone encontrado no Linux.")
    if rclone:
        supported = _command_ready([rclone, "help", "mount"])
        check("Comando rclone mount", supported,
              "rclone oferece montagem FUSE." if supported else
              "Este rclone não oferece montagem; atualize a instalação.")
        try:
            remotes = list_remotes(timeout=12)
            known = selected and remote in remotes
        except (OSError, subprocess.SubprocessError, ValueError):
            known = False
        check("Conta disponível ao rclone", known,
              "Remoto encontrado na configuração local." if known else
              "Conta ausente no rclone desta sessão. Confira rclone.conf.")
        # The user service uses a controlled system PATH for predictable mounts.
        standard = any(
            str(rclone).startswith(prefix) for prefix in
            ("/usr/bin/", "/usr/local/bin/", "/bin/"))
        check("Caminho do rclone para systemd", standard,
              "Executável acessível ao serviço do usuário." if standard else
              "Este rclone pode depender do PATH do terminal ou do Snap. "
              "Considere instalar em /usr/local/bin ou /usr/bin.")
    else:
        check("Comando rclone mount", False, "Indisponível sem rclone.")
        check("Conta disponível ao rclone", False, "Indisponível sem rclone.")
        check("Caminho do rclone para systemd", False, "Indisponível sem rclone.")

    helper = shutil.which("fusermount3") or shutil.which("fusermount")
    check("Helper FUSE", bool(helper),
          "fusermount instalado." if helper else
          "Instale fuse3 (sudo apt install fuse3).")
    device = Path("/dev/fuse")
    check("Dispositivo FUSE", device.exists(),
          "/dev/fuse encontrado." if device.exists() else
          "O dispositivo /dev/fuse não existe. Confirme módulo FUSE e permissões do Linux.")
    systemd = _command_ready(["systemctl", "--user", "show-environment"])
    check("Serviço do usuário", systemd,
          "systemd --user acessível." if systemd else
          "systemd --user indisponível; entre na sessão gráfica do Zorin.")

    if selected:
        try:
            mount = mount_path(remote, root)
            if mount_ready(mount):
                check("Diretório do disco virtual", True, "Unidade já montada.")
            else:
                validate_mount(config, root=root, require_tools=False, create=False)
                check("Diretório do disco virtual", True,
                      "Diretório vazio e separado da pasta espelhada.")
        except (OSError, ValueError, RuntimeError) as exc:
            # validate_mount uses only self-authored, bounded human-readable messages.
            check("Diretório do disco virtual", False, str(exc)[:180])

    problems = sum(not item["ok"] for item in results)
    return {"ready": problems == 0,
            "failed": problems, "checks": results,
            "note": ("Esses testes não acessam a nuvem. O Google ainda pode "
                     "recusar a montagem com erro 403 da API.")}


def format_mount_report(result):
    details = [
        ("✓ " if item["ok"] else "✕ ") + item["name"] + ": " + item["detail"]
        for item in result["checks"]]
    details.append(result["note"])
    return "\n".join(details)
