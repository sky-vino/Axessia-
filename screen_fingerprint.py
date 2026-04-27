# mobile/screen_fingerprint.py
import hashlib

def compute_screen_signature(screen: dict) -> str:
    """
    Compute a stable fingerprint for a screen based on its accessibility structure.
    """
    nodes = []

    for rule in screen.get("rules", []):
        for inst in rule.get("instances", []):
            key = (
                inst.get("role", ""),
                inst.get("component", ""),
                inst.get("bounds", "")
            )
            nodes.append("|".join(key))

    raw = "::".join(sorted(nodes))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
