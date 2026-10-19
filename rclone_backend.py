"""Safe shell-free rclone subprocess wrapper."""
import json
import re
import subprocess
from pathlib import Path
from rclone_errors import rclone_limits

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
                             '--max-depth', '1', '--no-mimetype'] + rclone_limits(),
                            capture_output=True, text=True, check=True, timeout=timeout)
    entries = json.loads(result.stdout)
    if not isinstance(entries, list):
        raise ValueError('Resposta inesperada do rclone')
    return [{'name': item['Name'], 'directory': bool(item.get('IsDir')),
             'size': item.get('Size', 0)} for item in entries
            if isinstance(item, dict) and isinstance(item.get('Name'), str)]

def copy_command(remote, local_folder, direction, preserve_newer=False, skip_existing=False):
    if direction not in ('upload', 'download'):
        raise ValueError('Direção inválida')
    local = Path(local_folder).expanduser()
    if not local.is_dir():
        raise ValueError('Pasta local não existe')
    cloud = remote_path(remote)
    source, dest = (str(local), cloud) if direction == 'upload' else (cloud, str(local))
    command = ['rclone', 'copy', source, dest, '--stats', '1s', '--stats-one-line', '--stats-log-level', 'NOTICE', '--log-level', 'NOTICE',
               '--retries', '3', '--low-level-retries', '5',
               '--transfers', '1', '--checkers', '1'] + rclone_limits()
    if skip_existing:
        if direction != 'download':
            raise ValueError('Proteção de arquivos existentes disponível somente para download')
        command.append('--ignore-existing')
    if preserve_newer:
        if direction != 'download':
            raise ValueError('Proteção automática disponível somente para download')
        command.append('--update')
    return command

def search_files(remote, term, timeout=120, limit=100):
    """Search a selected remote by path (read-only; no copies or deletes)."""
    remote_path(remote)
    if not isinstance(term, str) or not (2 <= len(term.strip()) <= 120):
        raise ValueError("Digite pelo menos 2 caracteres para pesquisar.")
    result = subprocess.run(
        ['rclone', 'lsjson', remote_path(remote), '--recursive', '--files-only',
         '--no-mimetype'] + rclone_limits(), capture_output=True, text=True, check=True, timeout=timeout)
    entries = json.loads(result.stdout)
    if not isinstance(entries, list):
        raise ValueError("Resposta de pesquisa inválida")
    needle = term.strip().casefold()
    return [{'name': item['Path'], 'directory': False,
             'size': item.get('Size', 0)}
            for item in entries
            if isinstance(item, dict) and isinstance(item.get('Path'), str)
            and needle in item['Path'].casefold()][:limit]
