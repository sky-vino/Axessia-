# android_rules_missing_label.py

def evaluate_missing_label(nodes: list) -> list:
    """
    WCAG 1.1.1 – Controls must have accessible labels.
    Returns list of failing instances.
    """

    instances = []

    for node in nodes:
        is_interactive = node["clickable"] or node["focusable"]

        if not is_interactive:
            continue

        if not node["visible"] or not node["enabled"]:
            continue

        if node["label"]:
            continue

        instances.append({
            "role": node["role"],
            "text": "",
            "bounds": f'{node["width"]}x{node["height"]}',
            "component": node.get("resource_id", ""),
            "reason": "Interactive control has no accessible label"
        })

    return instances
