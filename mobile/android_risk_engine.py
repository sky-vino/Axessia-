# android_risk_engine.py

SEVERITY_TO_RISK = {
    "critical": "high",
    "serious": "high",
    "moderate": "medium",
    "minor": "low"
}


def calculate_rule_risk(rule: dict) -> str:
    """
    Determines risk level for a single rule result.
    """
    if rule["status"] == "fail":
        return SEVERITY_TO_RISK.get(rule["severity"], "medium")

    if rule["status"] in ("assisted", "manual"):
        # Coverage gap → unknown risk
        return "medium"

    return "low"


def aggregate_screen_risk(rules: list) -> str:
    """
    Screen risk = max risk of all rules.
    """
    risks = [calculate_rule_risk(rule) for rule in rules]

    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    return "low"


def aggregate_app_risk(screens: list) -> str:
    """
    App risk = max risk of all screens.
    """
    risks = [screen["risk"] for screen in screens]

    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    return "low"
