# eaa_scoring_ios.py

SEVERITY_WEIGHT = {
    "critical": 30,
    "serious": 20,
    "moderate": 10,
    "minor": 5,
}

def compute_ios_eaa_score(rules):
    total = 0
    earned = 0

    for r in rules:
        weight = SEVERITY_WEIGHT.get(r["severity"], 5)
        total += weight

        if r["status"] == "pass":
            earned += weight
        elif r["status"] == "fail":
            earned += 0
        else:
            earned += 0  # not tested / NA → no credit

    return round((earned / total) * 100, 1) if total else 0.0


def compute_ios_risk(score):
    if score >= 80:
        return "low"
    if score >= 50:
        return "medium"
    return "high"
