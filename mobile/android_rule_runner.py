# android_rule_runner.py

from mobile.android_rules_missing_label import evaluate_missing_label
from mobile.android_rules_touch_target import evaluate_touch_target_size
from mobile.android_rules_focus_invisible import evaluate_focus_invisible
from mobile.android_rules_accessibility_disabled import evaluate_accessibility_disabled


def run_android_rules(nodes: list) -> list:
    results = []

    # Rule 1: Missing accessible label (1.1.1)
    label_instances = evaluate_missing_label(nodes)
    results.append({
        "id": "android-missing-label",
        "name": "Controls must have accessible labels",
        "wcag": "1.1.1",
        "level": "A",
        "test_type": "automated",
        "severity": "critical",
        "status": "fail" if label_instances else "pass",
        "instances": label_instances
    })

    # Rule 2: Touch target size (2.5.8)
    target_instances = evaluate_touch_target_size(nodes)
    results.append({
        "id": "android-touch-target-size",
        "name": "Touch targets must be at least 48x48dp",
        "wcag": "2.5.8",
        "level": "AA",
        "test_type": "automated",
        "severity": "serious",
        "status": "fail" if target_instances else "pass",
        "instances": target_instances
    })

    # Rule 3: Focusable but invisible (2.4.7)
    focus_invisible_instances = evaluate_focus_invisible(nodes)
    results.append({
        "id": "android-focus-invisible",
        "name": "Focusable elements must be visible",
        "wcag": "2.4.7",
        "level": "AA",
        "test_type": "automated",
        "severity": "serious",
        "status": "fail" if focus_invisible_instances else "pass",
        "instances": focus_invisible_instances
    })

    # Rule 4: Accessibility disabled on control (4.1.2)
    a11y_disabled_instances = evaluate_accessibility_disabled(nodes)
    results.append({
        "id": "android-accessibility-disabled",
        "name": "Interactive elements must not disable accessibility",
        "wcag": "4.1.2",
        "level": "A",
        "test_type": "automated",
        "severity": "critical",
        "status": "fail" if a11y_disabled_instances else "pass",
        "instances": a11y_disabled_instances
    })

    return results
