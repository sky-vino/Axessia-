# ======================================================
# AXESSIA – AI Engine (thin wrapper over ai_explainer)
# ======================================================

from ai_explainer import explain_rule


def ai_explain_issue(
    rule: str,
    wcag: str,
    severity: str,
    instance: dict | None = None,
) -> str:
    """Wrapper kept for backwards compatibility."""
    rule_dict = {
        "name":      rule,
        "wcag":      wcag,
        "severity":  severity,
        "test_type": "automated",
        "status":    "fail",
        "level":     "A",
    }
    result = explain_rule(rule=rule_dict, page_url="")
    return result.get("why_not_automated", "")
