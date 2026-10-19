"""Safe shell-free rclone subprocess wrapper."""
import json
import re
import subprocess
from pathlib import Path

REMOTE_RE = re.compile(r'^[^:\r\n/\\]+$')

def remote_path(name, relative=''):
    if not REMOTE_RE.fullmatch(name) or name in ('.', '..'):
        raise ValueError('Nome de conta inválido')
    if not isinstance(relative, str) or '\\' in relative or '\x00' in relative or relative.startswith('/') or '..' in Path(relative).parts:
        raise ValueError('Caminho remoto inválido')
    return name + ':' + relative

def list_remotes(timeout=15):
    result = subprocess.run(['rclone', 'listremotes'], capture_output=True,
                            text=True, check=True, timeout=timeout)
    return [line[:-1] for line in result.stdout.splitlines()
            if line.endswith(':') and REMOTE_RE.fullmatch(line[:-1])]

def list_files(remote, relative='', timeout=60):
    result = subprocess.run(['rclone', 'lsjson', remote_path(remote, relative),
                             '--max-depth', '1', '--no-mimetype'],
                            capture_output=True, text=True, check=True, timeout=timeout)
    entries = json.loads(result.stdout)
    if not isinstance(entries, list):
        raise ValueError('Resposta inesperada do rclone')
    return [{'name': item['Name'], 'directory': bool(item.get('IsDir')),
             'size': item.get('Size', 0)} for item in entries
            if isinstance(item, dict) and isinstance(item.get('Name'), str)]

def copy_command(remote, local_folder, direction):
    if direction not in ('upload', 'download'):
        raise ValueError('Direção inválida')
    local = Path(local_folder).expanduser()
    if not local.is_dir():
        raise ValueError('Pasta local não existe')
    cloud = remote_path(remote)
    source, dest = (str(local), cloud) if direction == 'upload' else (cloud, str(local))
    return ['rclone', 'copy', source, dest, '--stats', '5s', '--log-level', 'INFO',
            '--retries', '3', '--low-level-retries', '5']
