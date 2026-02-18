# eaa_scoring.py
# Canonical EAA scoring used across Web & Mobile

EAA_SEVERITY_WEIGHTS = {
    "critical": 4,
    "serious": 3,
    "moderate": 2,
    "minor": 1,
}

SCORE_MULTIPLIER = 5


def compute_eaa_score(rules: list[dict]) -> float:
    """
    Computes a numeric EAA score (0–100).
    Penalizes failures, assisted gaps, and manual gaps.
    """
    penalty = 0

    for r in rules:
        if r.get("status") in ("fail", "assisted", "manual"):
            weight = EAA_SEVERITY_WEIGHTS.get(r.get("severity"), 1)
            penalty += weight * SCORE_MULTIPLIER

    return max(0.0, 100.0 - penalty)


def compute_eaa_risk(score: float) -> str:
    if score >= 85:
        return "LOW"
    elif score >= 60:
        return "MEDIUM"
    return "HIGH"
