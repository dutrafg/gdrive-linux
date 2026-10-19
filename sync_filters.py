"""Conservative Insync-inspired selective/ignore rules for bidirectional mirroring.

Rules are applied identically to local and remote inventories *before* computing
actions or deletions. Excluding a path never deletes its existing copies.
No arbitrary shell commands, regular expressions or negated rclone filters.
"""
import fnmatch
import re

MAX_RULES = 40
MAX_RULE_LENGTH = 160

def validate_rule(rule):
    if not isinstance(rule, str):
        raise ValueError("Filtro deve ser texto.")
    rule = rule.strip()
    if not rule or len(rule) > MAX_RULE_LENGTH:
        raise ValueError("Filtro vazio ou muito longo.")
    if (rule.startswith("/") or rule.startswith("./")
            or "\\" in rule or "\x00" in rule
            or "//" in rule or rule.startswith("!")
            or ".." in rule.split("/")):
        raise ValueError("Filtro inválido: use caminhos relativos sem '../'.")
    return rule

def parse_rules(value):
    """Accept explicit lists from persistent settings, never unchecked objects."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_RULES:
        raise ValueError("Lista de filtros inválida (máximo 40).")
    return list(dict.fromkeys(validate_rule(rule) for rule in value))

def rule_matches(path, rule):
    # Folder-prefix rules also match their descendants and the folder itself.
    if rule.endswith("/"):
        prefix = rule.rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    # For *.tmp, match both bare names and files nested inside folders.
    if "/" not in rule:
        return fnmatch.fnmatchcase(path.rsplit("/", 1)[-1], rule)
    return fnmatch.fnmatchcase(path, rule)

def path_allowed(path, includes=(), excludes=()):
    if any(rule_matches(path, rule) for rule in excludes):
        return False
    return (not includes) or any(rule_matches(path, rule) for rule in includes)

def filtered_inventory(entries, includes=(), excludes=()):
    # Only file maps and explicit, validated rules are accepted.
    includes, excludes = parse_rules(list(includes)), parse_rules(list(excludes))
    return {path: fingerprint for path, fingerprint in entries.items()
            if path_allowed(path, includes, excludes)}

def parse_entry(text):
    """Split a GUI comma-separated list into validated patterns."""
    if not isinstance(text, str):
        raise ValueError("Filtros devem ser texto.")
    if not text.strip():
        return []
    entries = [part.strip() for part in text.split(",")]
    return parse_rules(entries)
