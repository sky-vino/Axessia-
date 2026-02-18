# prioritizer.py
# Layer 7 – Deterministic issue prioritisation

SEVERITY_WEIGHT = {
    "critical": 5,
    "serious": 3,
    "moderate": 1,
}

WCAG_LEVEL_WEIGHT = {
    "A": 3,
    "AA": 2,
    "AAA": 1,
}


def prioritize_issues(rules: list[dict], eaa: dict) -> list[dict]:
    """
    Returns a sorted remediation queue.
    Each item contains priority_score + reasoning.
    """

    queue = []
    blocking_wcag = set(eaa.get("blocking_wcag", []))

    for rule in rules:
        if rule["status"] != "fail":
            continue

        sev_score = SEVERITY_WEIGHT.get(rule["severity"], 1)
        wcag_score = WCAG_LEVEL_WEIGHT.get(rule["level"], 1)

        eaa_bonus = 5 if rule["wcag"] in blocking_wcag else 0
        automated_bonus = 2 if rule["test_type"] == "automated" else -2

        priority_score = (
            sev_score
            + wcag_score
            + eaa_bonus
            + automated_bonus
        )

        queue.append({
            "rule": rule["name"],
            "wcag": rule["wcag"],
            "severity": rule["severity"],
            "type": rule["test_type"],
            "priority_score": priority_score,
            "reasoning": {
                "severity_weight": sev_score,
                "wcag_level_weight": wcag_score,
                "eaa_bonus": eaa_bonus,
                "automated_bonus": automated_bonus,
            },
            "instances": rule.get("instances", []),
        })

    return sorted(
        queue,
        key=lambda x: x["priority_score"],
        reverse=True,
    )
