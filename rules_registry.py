# rules_registry.py

RULES = [

    # =========================
    # AUTOMATED RULES
    # =========================

    {
        "id": "image-alt",
        "name": "Images must have alt text",
        "wcag": "1.1.1",
        "level": "A",
        "test_type": "automated",
        "severity": "critical"
    },

    {
        "id": "keyboard-focus",
        "name": "Keyboard focus navigation",
        "wcag": "2.1.1",
        "level": "A",
        "test_type": "automated",
        "severity": "critical"
    },

    # =========================
    # ASSISTED RULES
    # =========================

    {
        "id": "focus-visible",
        "name": "Focus is clearly visible",
        "wcag": "2.4.7",
        "level": "AA",
        "test_type": "assisted",
        "severity": "moderate",
        "automated_assist": (
            "Verified that focusable elements are reachable via keyboard."
        ),
        "manual_remaining": (
            "Visually confirm focus indicator is clearly visible "
            "for all interactive elements during keyboard navigation."
        )
    },

    {
        "id": "form-errors",
        "name": "Form errors are identified",
        "wcag": "3.3.1",
        "level": "A",
        "test_type": "assisted",
        "severity": "serious",
        "automated_assist": (
            "Detected form inputs and aria-invalid usage where applicable."
        ),
        "manual_remaining": (
            "Confirm error messages are meaningful and announced by screen readers."
        )
    },

    # =========================
    # MANUAL RULES
    # =========================

    {
        "id": "keyboard-operable",
        "name": "Keyboard operability (manual verification)",
        "wcag": "2.1.1",
        "level": "A",
        "test_type": "manual",
        "severity": "critical",
        "manual_remaining": (
            "Navigate the entire site using only a keyboard "
            "(Tab, Shift+Tab, Enter, Arrow keys) and verify functionality."
        )
    }
]
