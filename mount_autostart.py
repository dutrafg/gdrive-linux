"""Autostart an optional rclone FUSE mount on desktop login.

Never enables system-wide services, root privileges or lingering.
The user-systemd unit survives app exit and can mount after user login.
"""
import subprocess

UNIT = "gdrive-linux-mount.service"

def systemctl_call(args, timeout=25, runner=None):
    runner = subprocess.run if runner is None else runner
    try:
        result = runner(["systemctl", "--user"] + list(args),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=timeout)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False

def autostart_enabled(runner=None):
    return systemctl_call(["is-enabled", "--quiet", UNIT], runner=runner)

def update_autostart(enable, runner=None):
    """Return (enabled_on_login, message); actual mount readiness is separate."""
    if type(enable) is not bool:
        raise ValueError("Estado inválido para montagem automática")
    if not systemctl_call(["daemon-reload"], runner=runner):
        return False, "Não foi possível atualizar serviços do usuário."
    if enable:
        if not systemctl_call(["enable", UNIT], runner=runner):
            return False, ("Falha ao habilitar a montagem na inicialização do usuário. "
                           "Verifique systemctl --user.")
        # Start asynchronously: Type=notify can require network/API for minutes.
        started = systemctl_call(["--no-block", "start", UNIT], runner=runner)
        if started:
            return True, ("Montagem automática habilitada para todas as próximas entradas "
                          "na sessão Linux. Primeira montagem solicitada.")
        return True, ("Montagem automática habilitada. A tentativa imediata falhou; "
                      "o serviço tentará novamente. Verifique o diagnóstico FUSE.")
    if not systemctl_call(["disable", UNIT], runner=runner):
        return True, "Não foi possível desabilitar a montagem automática."
    # Stop the existing mount as well; systemd waits for rclone to terminate.
    stopped = systemctl_call(["stop", UNIT], timeout=45, runner=runner)
    if not stopped:
        return False, ("Montagem automática desabilitada para as próximas sessões, "
                       "mas a desmontagem atual não foi concluída.")
    return False, "Montagem automática desativada e unidade desmontada."
