# android_accessibility_dump.py

from mobile.android_adb_client import run_adb


class AccessibilityDumpError(Exception):
    pass


def dump_accessibility_tree() -> str:
    """
    Dumps the accessibility node tree.
    Returns raw dump output.
    """
    try:
        # This relies on Android accessibility dump capability
        output = run_adb(
            "shell uiautomator dump /sdcard/axessia_a11y.xml"
        )
        xml = run_adb(
            "shell cat /sdcard/axessia_a11y.xml"
        )
        return xml
    except ADBError as e:
        raise AccessibilityDumpError(
            f"Failed to dump accessibility tree: {e}"
        )
