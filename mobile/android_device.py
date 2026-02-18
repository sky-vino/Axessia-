# android_device.py

from mobile.android_adb_client import run_adb, ADBError


class DeviceNotFoundError(Exception):
    pass


def get_connected_device() -> str:
    """
    Returns the single connected Android device ID.
    Raises if none or multiple devices are connected.
    """
    output = run_adb("devices")

    lines = output.splitlines()[1:]
    devices = [line.split()[0] for line in lines if "device" in line]

    if not devices:
        raise DeviceNotFoundError("No Android device connected")

    if len(devices) > 1:
        raise DeviceNotFoundError(
            "Multiple devices connected. Please connect only one device."
        )

    return devices[0]
