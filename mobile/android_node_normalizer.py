# android_node_normalizer.py

import re


def _parse_bounds(bounds: str) -> dict:
    """
    Converts Android bounds string to width/height.
    Example: [0,123][1080,321]
    """
    match = re.findall(r"\[(\d+),(\d+)\]", bounds)
    if len(match) != 2:
        return {"width": 0, "height": 0}

    (x1, y1), (x2, y2) = match
    return {
        "width": int(x2) - int(x1),
        "height": int(y2) - int(y1)
    }


def normalize_android_nodes(raw_nodes: list) -> list:
    """
    Normalizes raw accessibility nodes into Axessia-friendly format.
    """
    normalized = []

    for node in raw_nodes:
        label = node["content_desc"] or node["text"]

        bounds = _parse_bounds(node["bounds"])

        normalized.append({
            "role": node["class"].split(".")[-1],
            "label": label.strip(),
            "clickable": node["clickable"],
            "focusable": node["focusable"],
            "enabled": node["enabled"],
            "visible": node["visible"],
            "width": bounds["width"],
            "height": bounds["height"],
            "resource_id": node["resource_id"]
        })

    return normalized
