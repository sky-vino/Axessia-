# ai_explainer.py

def explain_rule(rule: dict, page_url: str) -> dict:
    """
    AI Explainer v2
    Generates contextual, rule-aware explanations.
    No static text, no rule-specific hardcoding.
    """

    rule_desc = rule.get("name") or rule.get("id")
    wcag = rule.get("wcag")
    level = rule.get("level")
    severity = rule.get("severity")
    rule_type = rule.get("test_type")
    status = rule.get("status")
    instance_count = rule.get("instance_count", 0)

    if rule_type == "automated":
        why_not_automated = (
            "This rule is suitable for automated detection because its "
            "requirements can be programmatically verified."
        )
    else:
        why_not_automated = (
            f"The rule '{rule_desc}' cannot be fully automated because "
            f"compliance depends on user interaction, visual perception, "
            f"or contextual intent."
        )

    if rule_type == "automated":
        what_to_test_manually = (
            "No manual verification is required unless false positives are suspected."
        )
    else:
        what_to_test_manually = (
            f"Manually verify '{rule_desc}' by testing real user flows "
            f"using keyboard and assistive technologies."
        )

    if rule_type == "assisted":
        automated_vs_not = (
            "Automation can detect related patterns, but human validation "
            "is required to confirm usability and intent."
        )
    elif rule_type == "manual":
        automated_vs_not = (
            "There is no reliable automated detection for this rule. "
            "Human evaluation is required."
        )
    else:
        automated_vs_not = (
            "Detection and validation are handled entirely through automation."
        )

    who_is_impacted = (
        "Users relying on keyboards, screen readers, or other assistive "
        "technologies may be impacted."
    )

    legal_risk = (
        f"Non-compliance with WCAG {wcag} (Level {level}) may pose legal risk."
        if status != "pass"
        else "This rule currently meets WCAG requirements."
    )

    qa_steps = []
    if rule_type != "automated":
        qa_steps = [
            "Navigate using keyboard only (Tab / Shift+Tab)",
            "Verify focus order and visibility",
            "Test with a screen reader",
            "Confirm expected behavior"
        ]

    return {
        "why_not_automated": why_not_automated,
        "what_to_test_manually": what_to_test_manually,
        "what_is_automated_vs_not": automated_vs_not,
        "who_is_impacted": who_is_impacted,
        "legal_risk": legal_risk,
        "qa_validation_steps": qa_steps,
    }
