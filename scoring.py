# scoring.py
# Layer 5 – Deterministic WCAG scoring

SEVERITY_WEIGHTS = {
    "critical": 5,
    "serious": 3,
    "moderate": 1,
}


def calculate_score(rules: list[dict]) -> dict:
    """
    Scoring rules:
    - Only AUTOMATED rules affect score
    - FAIL → penalty based on severity
    - MANUAL / ASSISTED → do NOT increase score
    """

    automated = [r for r in rules if r["test_type"] == "automated"]

    if not automated:
        return {
            "score": 100,
            "breakdown": {},
            "note": "No automated rules evaluated",
        }

    max_penalty = sum(
        SEVERITY_WEIGHTS.get(r["severity"], 1)
        for r in automated
    )

    penalty = 0
    breakdown = {}

    for r in automated:
        sev = r["severity"]
        breakdown.setdefault(sev, {"pass": 0, "fail": 0})

        if r["status"] == "fail":
            penalty += SEVERITY_WEIGHTS.get(sev, 1)
            breakdown[sev]["fail"] += 1
        else:
            breakdown[sev]["pass"] += 1

    score = max(0, round(100 - (penalty / max_penalty) * 100, 1))

    return {
        "score": score,
        "breakdown": breakdown,
        "max_penalty": max_penalty,
        "penalty": penalty,
    }
