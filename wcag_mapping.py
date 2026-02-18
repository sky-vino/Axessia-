# wcag_mapping.py

# Canonical WCAG + Axe rule registry
# This is the SINGLE source of truth

WCAG_RULES = {
    # ---- AUTOMATED (AXE) ----
    "color-contrast": {
        "rule_id": "color-contrast",
        "title": "Text contrast is sufficient",
        "wcag": "1.4.3",
        "level": "AA",
        "severity": "serious",
        "type": "automated",
    },
    "image-alt": {
        "rule_id": "image-alt",
        "title": "Images have alternative text",
        "wcag": "1.1.1",
        "level": "A",
        "severity": "critical",
        "type": "automated",
    },
    "button-name": {
        "rule_id": "button-name",
        "title": "Buttons have accessible names",
        "wcag": "4.1.2",
        "level": "A",
        "severity": "critical",
        "type": "automated",
    },
    "link-name": {
        "rule_id": "link-name",
        "title": "Links have accessible names",
        "wcag": "2.4.4",
        "level": "A",
        "severity": "serious",
        "type": "automated",
    },
    "html-has-lang": {
        "rule_id": "html-has-lang",
        "title": "HTML document has a lang attribute",
        "wcag": "3.1.1",
        "level": "A",
        "severity": "serious",
        "type": "automated",
    },

    # ---- MANUAL ----
    "keyboard-operability": {
        "rule_id": "keyboard-operability",
        "title": "Keyboard operability",
        "wcag": "2.1.1",
        "level": "A",
        "severity": "critical",
        "type": "manual",
    },
    "focus-visible": {
        "rule_id": "focus-visible",
        "title": "Focus is clearly visible",
        "wcag": "2.4.7",
        "level": "AA",
        "severity": "moderate",
        "type": "manual",
    },

    # ---- ASSISTED ----
    "error-identification": {
        "rule_id": "error-identification",
        "title": "Errors are clearly identified",
        "wcag": "3.3.1",
        "level": "AA",
        "severity": "serious",
        "type": "assisted",
    },
    "headings-order": {
        "rule_id": "headings-order",
        "title": "Headings follow a logical order",
        "wcag": "1.3.1",
        "level": "A",
        "severity": "moderate",
        "type": "assisted",
    },
}

def resolve_rule(rule_id: str) -> dict:
    """
    Always returns a COMPLETE rule object.
    Never returns None.
    """
    if rule_id in WCAG_RULES:
        return WCAG_RULES[rule_id]

    # Safe fallback for unknown axe rules
    return {
        "rule_id": rule_id,
        "title": rule_id.replace("-", " ").title(),
        "wcag": "N/A",
        "level": "A",
        "severity": "moderate",
        "type": "automated",
    }
