"""Human-readable rclone error classification without disclosing API traces."""
from datetime import datetime, timedelta, timezone

RATE_LIMIT_HINT = ("A API do Google Drive bloqueou consultas por excesso de requisições "
                   "(403). Pause transferências, aguarde a recuperação da cota e "
                   "configure um Client ID e Client Secret próprios no rclone. "
                   "A chave compartilhada pode continuar bloqueada mesmo com menos consultas.")
QUOTA_DELAY_MINUTES = 15

def is_rate_limit(message):
    if not isinstance(message, str):
        return False
    lower = message.lower()
    return any(x in lower for x in (
        "ratelimitexceeded", "rate_limit_exceeded",
        "userratelimitexceeded", "userqueriesperminuteperproject",
        "quota exceeded", "quota_exceeded", "too many requests",
        "api do google drive bloqueou consultas"
    ))

def friendly(message):
    if is_rate_limit(message):
        return RATE_LIMIT_HINT
    lower = str(message).lower()
    if "read-only file system" in lower or "permission denied" in lower:
        return ("Sem permissão de gravação. Confira se o disco virtual está "
                "em modo leitura, o acesso da conta e as permissões da pasta.")
    if "invalid_grant" in lower or "token expired" in lower:
        return "O Google rejeitou a autorização. Reconecte esta conta pelo rclone."
    if "couldn't find root directory" in lower:
        return ("Não foi possível consultar a raiz do Google Drive. "
                "Confirme as credenciais OAuth próprias e a cota da API.")
    if "no space left on device" in lower or "disk full" in lower:
        return "O armazenamento local está cheio. Libere espaço e tente novamente."
    if ("mudou durante" in lower or "arquivo alterado" in lower
            or "link simbólico" in lower or "links rígidos" in lower):
        return ("Um arquivo ou caminho local mudou ou não é seguro. "
                "A transferência foi suspensa; verifique a pasta.")
    if ("network is unreachable" in lower or "connection refused" in lower
            or "connection reset" in lower or "timeout" in lower
            or "timed out" in lower or "drive offline" in lower):
        return "Conexão indisponível ou tempo limite excedido. Os arquivos permanecem para retentativa."
    if "não está montado" in lower or "transport endpoint" in lower:
        return "O disco externo ou FUSE não está montado. Reconecte antes de tentar novamente."
    if "histórico de sincronização" in lower:
        return "Histórico de sincronização inválido. Recupere o estado anterior antes de prosseguir."
    return "Erro de acesso ao Drive. Consulte o diagnóstico da conta."

def quota_retry_after(now=None):
    now = now or datetime.now(timezone.utc)
    return (now + timedelta(minutes=QUOTA_DELAY_MINUTES)).isoformat()

def cooldown_active(status, now=None):
    if not isinstance(status, dict) or status.get("state") != "quota":
        return False
    until = status.get("retry_after")
    try:
        until_dt = datetime.fromisoformat(until)
        if until_dt.tzinfo is None:
            return False
        return (now or datetime.now(timezone.utc)) < until_dt
    except (ValueError, TypeError):
        return False

def rclone_limits():
    """Limit this application's calls; cannot fix exhausted shared project quota."""
    return ["--tpslimit", "2", "--tpslimit-burst", "2"]
