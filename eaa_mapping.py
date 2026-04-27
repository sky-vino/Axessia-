# eaa_mapping.py
# EAA (European Accessibility Act) readiness mapping
# Based on EN 301 549 which references WCAG 2.1 AA

# All WCAG A + AA criteria are EAA mandatory
EAA_MANDATORY_LEVELS = {"A", "AA"}

# These criteria are highest risk for EAA non-compliance enforcement
EAA_CRITICAL_WCAG = {
    "1.1.1",   # Non-text content — images without alt
    "1.3.1",   # Info and relationships — form labels, headings
    "1.3.5",   # Identify input purpose — autocomplete
    "1.4.3",   # Contrast minimum
    "1.4.4",   # Resize text — zoom not blocked
    "1.4.10",  # Reflow — mobile
    "1.4.11",  # Non-text contrast
    "1.4.12",  # Text spacing
    "2.1.1",   # Keyboard accessible
    "2.1.2",   # No keyboard trap
    "2.4.2",   # Page titled
    "2.4.3",   # Focus order
    "2.4.4",   # Link purpose
    "2.4.7",   # Focus visible
    "2.4.11",  # Focus not obscured (WCAG 2.2)
    "2.5.8",   # Target size (WCAG 2.2)
    "3.1.1",   # Language of page
    "3.3.1",   # Error identification
    "3.3.8",   # Accessible authentication (WCAG 2.2)
    "4.1.2",   # Name, role, value
    "4.1.3",   # Status messages
}


def evaluate_eaa(rules: list[dict]) -> dict:
    """
    Full EAA readiness evaluation.
    - ANY failure in mandatory WCAG A/AA → not ready
    - Critical WCAG failures flagged separately
    - Manual/assisted gaps flagged as review required
    """
    from wcag_master_map import WCAG_SC_LEVEL, WCAG_SC_NAME

    failed_critical = []
    failed_aa = []
    manual_review = []
    passed_count = 0
    total_automated = 0

    for r in rules:
        wcag = r.get("wcag", "")
        level = WCAG_SC_LEVEL.get(wcag, r.get("level", ""))
        status = r.get("status")
        test_type = r.get("test_type")
        name = WCAG_SC_NAME.get(wcag, r.get("name", wcag))

        if test_type == "automated":
            total_automated += 1
            if status == "pass":
                passed_count += 1
            elif status == "fail":
                entry = {
                    "wcag": wcag,
                    "name": name,
                    "level": level,
                    "severity": r.get("severity"),
                    "instance_count": r.get("instance_count", 0),
                }
                if wcag in EAA_CRITICAL_WCAG:
                    failed_critical.append(entry)
                elif level in EAA_MANDATORY_LEVELS:
                    failed_aa.append(entry)

        if test_type in ("manual", "assisted"):
            manual_review.append({
                "wcag": wcag,
                "name": r.get("name"),
                "test_type": test_type,
            })

    eaa_ready = len(failed_critical) == 0 and len(failed_aa) == 0

    # Risk level
    if len(failed_critical) >= 3:
        risk = "HIGH"
    elif len(failed_critical) >= 1 or len(failed_aa) >= 3:
        risk = "MEDIUM"
    elif manual_review:
        risk = "REVIEW"
    else:
        risk = "LOW"

    return {
        "eaa_ready": eaa_ready,
        "risk_level": risk,
        "failed_critical_count": len(failed_critical),
        "failed_aa_count": len(failed_aa),
        "failed_critical": failed_critical,
        "failed_aa": failed_aa,
        "manual_review_required": bool(manual_review),
        "manual_review_items": manual_review,
        "automated_pass_rate": round(
            (passed_count / total_automated * 100), 1
        ) if total_automated else 0.0,
        "blocking_wcag": sorted(
            set(e["wcag"] for e in failed_critical + failed_aa)
        ),
    }
