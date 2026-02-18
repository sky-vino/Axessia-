# android_worker.py

from mobile.android_device import get_connected_device
from mobile.android_app_state import verify_app_in_foreground
from mobile.android_accessibility_dump import dump_accessibility_tree
from mobile.android_accessibility_parser import parse_accessibility_xml
from mobile.android_node_normalizer import normalize_android_nodes
from mobile.android_rule_runner import run_android_rules
from mobile.android_assisted_manual_rules import (
    get_assisted_rules,
    get_manual_rules
)
from mobile.android_risk_engine import (
    aggregate_screen_risk,
    aggregate_app_risk
)


def run_android_scan(
    app_package: str,
    assistive_context: dict,
    progress_cb=None
) -> dict:

    if progress_cb:
        progress_cb("Validating device")

    device_id = get_connected_device()

    if progress_cb:
        progress_cb("Validating foreground app")

    verify_app_in_foreground(app_package)

    if progress_cb:
        progress_cb("Capturing accessibility tree")

    raw_xml = dump_accessibility_tree()

    if progress_cb:
        progress_cb("Parsing accessibility data")

    raw_nodes = parse_accessibility_xml(raw_xml)

    if progress_cb:
        progress_cb("Normalizing accessibility nodes")

    normalized_nodes = normalize_android_nodes(raw_nodes)

    if progress_cb:
        progress_cb("Running automated rules")

    automated_rules = run_android_rules(normalized_nodes)

    if progress_cb:
        progress_cb("Registering assisted and manual rules")

    assisted_rules = get_assisted_rules()
    manual_rules = get_manual_rules()

    all_rules = automated_rules + assisted_rules + manual_rules

    screen_risk = aggregate_screen_risk(all_rules)

    screen_result = {
        "name": "Current Screen",
        "risk": screen_risk,
        "rules": all_rules
    }

    app_risk = aggregate_app_risk([screen_result])

    if progress_cb:
        progress_cb("Scan completed")

    return {
        "platform": "android",
        "device_id": device_id,
        "app_package": app_package,
        "assistive_context": assistive_context,
        "app_risk": app_risk,
        "screens": [screen_result]
    }
