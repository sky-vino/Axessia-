# android_rules_accessibility_disabled.py

def evaluate_accessibility_disabled(nodes: list) -> list:
    """
    WCAG 4.1.2 – Interactive elements must not disable accessibility.
    """

    instances = []

    for node in nodes:
        is_interactive = node.get("clickable") or node.get("focusable")
        if not is_interactive:
            continue

        if not node.get("visible"):
            continue

        if node.get("enabled"):
            continue

        instances.append({
            "role": node.get("role"),
            "bounds": f'{node.get("width")}x{node.get("height")}',
            "component": node.get("resource_id", ""),
            "reason": "Interactive element is disabled for accessibility"
        })

    return instances
