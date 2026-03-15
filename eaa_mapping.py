# eaa_mapping.py
# Layer 5 – EAA readiness mapping (rule-based, no AI)

EAA_CRITICAL_WCAG = {
    "1.1.1",  # Non-text content
    "1.3.1",  # Info and relationships
    "2.1.1",  # Keyboard
    "2.4.7",  # Focus visible
    "3.3.1",  # Error identification
}


def evaluate_eaa(rules: list[dict]) -> dict:
    """
    EAA logic:
    - ANY failure in critical WCAG → not ready
    - ANY manual rule → needs review
    """

    failed_wcag = set()
    manual_rules = []

    for r in rules:
        if r["wcag"] in EAA_CRITICAL_WCAG:
            if r["status"] == "fail":
                failed_wcag.add(r["wcag"])

        if r["test_type"] in ("manual", "assisted"):
            manual_rules.append(r["name"])

    return {
        "eaa_ready": not failed_wcag,
        "blocking_wcag": sorted(failed_wcag),
        "manual_review_required": bool(manual_rules),
        "manual_rules": manual_rules,
    }
