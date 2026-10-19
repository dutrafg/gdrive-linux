"""Read-only sync status formatting shared by desktop diagnostics.

No raw rclone stderr, tokens, paths or file names are included.
"""
from datetime import datetime, timedelta, timezone

LABELS = {
    "ok": "Concluída",
    "partial": "Aguardando próximos ciclos",
    "busy": "Em execução",
    "conflicts": "Conflitos pendentes",
    "quota": "API Google temporariamente limitada",
    "error": "Falha na sincronização",
    "disabled": "Desativada",
    "preview": "Simulação",
}
MODES = {"upload": "Enviar", "download": "Baixar",
         "bidirectional": "Bidirecional"}

def clean_remote_label(value):
    """Allow simple account identifiers without exposing paths or newlines."""
    if not isinstance(value, str):
        return "conta desconhecida"
    label = "".join(c for c in value if c.isprintable() and c not in "/\\")
    return label[:45] or "conta desconhecida"

def profile_lines(state, max_profiles=4):
    """Summarize at most a few accounts to avoid GTK label overflow."""
    if not isinstance(state, dict):
        return []
    profiles = state.get("profiles")
    if not isinstance(profiles, list):
        return []
    lines = []
    for item in profiles[:max_profiles]:
        if not isinstance(item, dict):
            continue
        name = clean_remote_label(item.get("account"))
        mode = MODES.get(item.get("mode"), "")
        title = LABELS.get(item.get("state"), "Estado desconhecido")
        copied = max(0, int(item.get("copied", 0) or 0))
        pending = max(0, int(item.get("pending", 0) or 0))
        summary = name + ": " + title
        if mode:
            summary += " (" + mode + ")"
        if copied or pending:
            summary += " — " + str(copied) + " transferido(s), " + str(pending) + " pendente(s)"
        lines.append(summary)
    if len(profiles) > max_profiles:
        lines.append("… e mais " + str(len(profiles) - max_profiles) + " conta(s).")
    return lines

def last_activity_age(state, now=None):
    """Return a warning for stale recorded cycles, never a false live status."""
    if not isinstance(state, dict):
        return ""
    value = state.get("time")
    if not isinstance(value, str):
        return ""
    try:
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None:
            return ""
    except ValueError:
        return ""
    now = now or datetime.now(timezone.utc)
    age = now - stamp
    if age > timedelta(minutes=15):
        return "Última verificação há mais de 15 minutos; confira o timer do Linux."
    return ""
