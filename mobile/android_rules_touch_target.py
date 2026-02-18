# android_rules_touch_target.py

MIN_TARGET_DP = 48


def evaluate_touch_target_size(nodes: list) -> list:
    """
    WCAG 2.5.8 – Touch targets must be at least 48x48dp.
    """

    instances = []

    for node in nodes:
        is_interactive = node["clickable"] or node["focusable"]

        if not is_interactive:
            continue

        if not node["visible"] or not node["enabled"]:
            continue

        if node["width"] < MIN_TARGET_DP or node["height"] < MIN_TARGET_DP:
            instances.append({
                "role": node["role"],
                "bounds": f'{node["width"]}x{node["height"]}',
                "component": node.get("resource_id", ""),
                "reason": "Touch target smaller than 48x48dp"
            })

    return instances
