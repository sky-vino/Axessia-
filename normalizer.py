# normalizer.py

from wcag_master_map import WCAG_SC_LEVEL

SEVERITY_MAP = {
    "critical": 5,
    "serious": 4,
    "moderate": 3,
    "minor": 2,
    None: 1,
}

def normalize_severity(impact: str) -> str:
    if not impact:
        return "minor"
    return impact.lower()

def severity_weight(severity: str) -> int:
    return SEVERITY_MAP.get(severity, 1)

def resolve_wcag_level(wcag_sc: str) -> str:
    if not wcag_sc or wcag_sc == "—":
        return "—"
    return WCAG_SC_LEVEL.get(wcag_sc, "—")
