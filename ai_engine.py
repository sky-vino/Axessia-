from ai_explainer import ai_explain_issue as _ai_explain_issue

def ai_explain_issue(
    rule: str,
    wcag: str,
    severity: str,
    instance: dict | None = None
) -> str:
    return _ai_explain_issue(
        rule=rule,
        wcag=wcag,
        severity=severity,
        instance=instance
    )
