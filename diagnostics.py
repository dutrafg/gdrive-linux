"""Read-only Linux readiness diagnostics; never print credentials or tokens."""
import json
import os
import shutil
import subprocess
from pathlib import Path

from settings import load_settings
from mount_drive import mount_path
from mount_health import mount_diagnosis

def run_probe(argv, timeout=15):
    try:
        result = subprocess.run(argv, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=timeout)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False

def collect_diagnostics(config=None):
    config = load_settings() if config is None else config
    items = []
    def add(name, passed, detail):
        items.append({"name": name, "ok": bool(passed), "detail": detail})

    exists = shutil.which("rclone") is not None
    add("rclone", exists, "Instalado" if exists else
        "Não encontrado. Instale seguindo https://rclone.org/install/")
    has_systemd = run_probe(["systemctl", "--user", "show-environment"])
    add("Serviço systemd do usuário", has_systemd,
        "Disponível" if has_systemd else
        "Indisponível; faça login em uma sessão desktop do Zorin OS.")
    timer_ok = run_probe(["systemctl", "--user", "is-active", "gdrive-linux-sync.timer"])
    add("Sincronização automática", timer_ok,
        "Timer ativo" if timer_ok else
        "Timer inativo; ative em Sincronização se desejar.")
    local = config.get("folder")
    folder = Path(local).expanduser() if isinstance(local, str) and local else None
    good_folder = bool(folder and folder.is_dir() and os.access(folder, os.W_OK))
    add("Pasta local", good_folder,
        "Disponível para escrita" if good_folder else
        "Pasta inexistente ou sem permissão de escrita.")
    remote = config.get("account")
    if isinstance(remote, str) and remote and exists:
        connected = run_probe(["rclone", "lsd", remote + ":"], timeout=45)
        add("Acesso à conta Google", connected,
            "Consulta remota concluída" if connected else
            "Não foi possível acessar o remoto configurado.")
    else:
        add("Acesso à conta Google", False, "Selecione uma conta no aplicativo.")
    fuse = (Path("/dev/fuse").exists() and bool(shutil.which("fusermount3")
                                                or shutil.which("fusermount")))
    add("Suporte FUSE", fuse, "Pronto para testar montagem" if fuse else
        "Instale fuse3 e confirme a existência de /dev/fuse.")
    if isinstance(remote, str) and remote:
        try:
            mounted = mount_path(remote).is_mount()
        except ValueError:
            mounted = False
        add("Disco virtual", mounted, "Montado" if mounted else
            mount_diagnosis(mount_path(remote)))
    return items

def format_report(items):
    return "\n".join(("✓ " if item["ok"] else "• ") + item["name"] +
                     " — " + item["detail"] for item in items)

if __name__ == "__main__":
    print(json.dumps(collect_diagnostics(), ensure_ascii=False, indent=2))
