# android_rules_focus_invisible.py

def evaluate_focus_invisible(nodes: list) -> list:
    """
    WCAG 2.4.7 – Focusable elements must be visible.
    """

    instances = []

    for node in nodes:
        if not node.get("focusable"):
            continue

        if node.get("visible"):
            continue

        if not node.get("enabled"):
            continue

        instances.append({
            "role": node.get("role"),
            "bounds": f'{node.get("width")}x{node.get("height")}',
            "component": node.get("resource_id", ""),
            "reason": "Element is focusable but not visible to user"
        })

    return instances
