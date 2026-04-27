# ai_mobile_explainer.py
"""
Mobile Accessibility AI Explanations
Read-only, audit-safe, no remediation promises
Includes Dev vs QA framing
"""

MOBILE_RULE_EXPLANATIONS = {

    "android-missing-label": {
        "title": "Missing accessible label",
        "user_impact": (
            "Screen reader users rely on labels to understand controls. "
            "Without a label, TalkBack may announce unclear or meaningless information."
        ),
        "why_it_matters": (
            "This can block task completion for blind and low-vision users, "
            "especially in forms and transactional flows."
        ),
        "dev_notes": (
            "Ensure interactive views expose meaningful accessibility labels "
            "via contentDescription or associated text."
        ),
        "qa_notes": (
            "Enable TalkBack and swipe through controls. Verify each control "
            "is announced with a clear, descriptive label."
        ),
        "wcag": "1.1.1 Non-text Content",
        "eaa_context": "High EAA risk on primary user journeys."
    },

    "android-focus-invisible": {
        "title": "Focusable element not visible",
        "user_impact": (
            "TalkBack users may hear elements that are not visually visible, "
            "causing loss of orientation and confusion."
        ),
        "why_it_matters": (
            "Invisible focus breaks spatial understanding and reduces trust in the interface."
        ),
        "dev_notes": (
            "Avoid focusable elements that are off-screen or hidden. "
            "Review visibility and importantForAccessibility settings."
        ),
        "qa_notes": (
            "With TalkBack enabled, swipe through the screen and confirm "
            "focus only lands on visible UI elements."
        ),
        "wcag": "2.4.7 Focus Visible",
        "eaa_context": "High risk for public-facing and regulated apps."
    },

    "android-touch-target-size": {
        "title": "Touch target too small",
        "user_impact": (
            "Users with motor impairments may struggle to activate small touch targets accurately."
        ),
        "why_it_matters": (
            "Small targets increase error rates and frustration for many users."
        ),
        "dev_notes": (
            "Ensure interactive elements meet minimum touch target size guidelines."
        ),
        "qa_notes": (
            "Verify controls can be activated reliably without precision tapping."
        ),
        "wcag": "2.5.8 Target Size (Minimum)",
        "eaa_context": "Moderate EAA risk depending on frequency."
    },

    "android-focus-order": {
        "title": "Unclear focus order",
        "user_impact": (
            "Screen reader users may receive content in an illogical sequence."
        ),
        "why_it_matters": (
            "Poor focus order increases cognitive load and reduces usability."
        ),
        "dev_notes": (
            "Review layout hierarchy and traversal order to match visual flow."
        ),
        "qa_notes": (
            "Navigate using TalkBack gestures and confirm logical reading order."
        ),
        "wcag": "2.4.3 Focus Order",
        "eaa_context": "Moderate to high risk on complex screens."
    },

    "android-gesture-alternatives": {
        "title": "Gesture without accessible alternative",
        "user_impact": (
            "Users unable to perform complex gestures may be blocked from functionality."
        ),
        "why_it_matters": (
            "Gesture-only interactions exclude users with motor impairments."
        ),
        "dev_notes": (
            "Provide accessible alternatives for gesture-based interactions."
        ),
        "qa_notes": (
            "Verify all functionality is reachable without complex gestures."
        ),
        "wcag": "2.5.1 Pointer Gestures",
        "eaa_context": "High EAA risk if no alternative exists."
    },
}


def get_mobile_ai_explanation(rule_id: str):
    return MOBILE_RULE_EXPLANATIONS.get(rule_id)
