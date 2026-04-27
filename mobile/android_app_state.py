# android_app_state.py

from mobile.android_adb_client import run_adb, ADBError


class AppNotInForegroundError(Exception):
    pass


def verify_app_in_foreground(package_name: str) -> None:
    """
    Verifies that the given app package is currently in the foreground.
    Compatible with modern Android versions (Android 11+).
    """

    try:
        output = run_adb(
            "shell dumpsys activity activities"
        )
    except ADBError as e:
        raise AppNotInForegroundError(
            f"Unable to determine foreground app: {e}"
        )

    # Look for ResumedActivity or topResumedActivity
    if package_name not in output:
        raise AppNotInForegroundError(
            f"App '{package_name}' is not in foreground"
        )
