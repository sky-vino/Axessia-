# android_adb_client.py

import subprocess
import shlex
import logging

ADB_TIMEOUT = 10


class ADBError(Exception):
    pass


def run_adb(command: str) -> str:
    """
    Runs an adb command safely.
    Raises ADBError on failure.
    """
    full_cmd = f"adb {command}"
    logging.debug(f"ADB CMD: {full_cmd}")

    try:
        result = subprocess.run(
            shlex.split(full_cmd),
            capture_output=True,
            text=True,
            timeout=ADB_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        raise ADBError("ADB command timed out")

    if result.returncode != 0:
        raise ADBError(result.stderr.strip())

    return result.stdout.strip()
