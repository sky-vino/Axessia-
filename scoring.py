# scoring.py
# Weighted accessibility scoring
# Factors: severity, instance count, viewport coverage

SEVERITY_WEIGHTS = {
    "critical": 5,
    "serious":  3,
    "moderate": 1,
    "minor":    0.5,
}

# Instance count multiplier — capped to avoid one rule dominating
def _instance_multiplier(count: int) -> float:
    if count <= 1:   return 1.0
    if count <= 5:   return 1.5
    if count <= 15:  return 2.0
    return 2.5


def calculate_score(rules: list[dict]) -> dict:
    """
    Weighted WCAG score (0–100).
    - Only automated rules affect the score
    - Severity × instance count multiplier
    - Returns score + breakdown by severity + per-WCAG stats
    """
    automated = [r for r in rules if r.get("test_type") == "automated"]

    if not automated:
        return {
            "score": 100.0,
            "breakdown": {},
            "note": "No automated rules evaluated",
            "total_issues": 0,
            "total_instances": 0,
        }

    max_possible = sum(
        SEVERITY_WEIGHTS.get(r["severity"], 1)
        for r in automated
    )

    penalty      = 0.0
    breakdown    = {}
    wcag_summary = {}
    total_instances = 0

    for r in automated:
        sev    = r.get("severity", "moderate")
        status = r.get("status")
        count  = r.get("instance_count", 0) or (1 if status == "fail" else 0)
        wcag   = r.get("wcag", "—")

        breakdown.setdefault(sev, {"pass": 0, "fail": 0, "instances": 0})
        wcag_summary.setdefault(wcag, {"pass": 0, "fail": 0})

        if status == "fail":
            base_weight = SEVERITY_WEIGHTS.get(sev, 1)
            multiplier  = _instance_multiplier(count)
            weighted    = base_weight * multiplier
            # Cap penalty per rule to prevent single rule destroying score
            weighted    = min(weighted, base_weight * 3)
            penalty    += weighted

            breakdown[sev]["fail"]     += 1
            breakdown[sev]["instances"]+= count
            wcag_summary[wcag]["fail"] += 1
            total_instances            += count
        else:
            breakdown[sev]["pass"]     += 1
            wcag_summary[wcag]["pass"] += 1

    score = max(0.0, round(100.0 - (penalty / max(max_possible, 1)) * 100, 1))

    return {
        "score":           score,
        "breakdown":       breakdown,
        "wcag_summary":    wcag_summary,
        "max_possible":    max_possible,
        "penalty":         round(penalty, 2),
        "total_issues":    sum(b["fail"] for b in breakdown.values()),
        "total_instances": total_instances,
    }
