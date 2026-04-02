import argparse
import subprocess
import time

def run_cmd(cmd):
    subprocess.run(cmd, capture_output=True, text=True)

def check_device():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    return "device" in result.stdout

def launch_app(package):
    print(f"[INFO] Launching app: {package}")
    run_cmd([
        "adb", "shell", "monkey",
        "-p", package,
        "-c", "android.intent.category.LAUNCHER",
        "1"
    ])
    time.sleep(3)

def dump_ui(index):
    print(f"[INFO] Capturing screen {index}")
    run_cmd(["adb", "shell", "uiautomator", "dump"])
    run_cmd(["adb", "pull", "/sdcard/window_dump.xml", f"window_dump_{index}.xml"])

def send_to_azure(file_path, session_id, azure_url, package_name):
    print(f"[INFO] Sending {file_path} to Azure...")
    print("[INFO] Azure response: 200 (demo mode)")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument("--azure", required=True)
    parser.add_argument("--screens", type=int, default=2)

    args = parser.parse_args()

    print("\n=== MOBILE SCAN RUNNER STARTED ===")

    if not check_device():
        print("[ERROR] No device connected")
        return

    print("[INFO] Device connected")

    launch_app(args.app)

    for i in range(args.screens):
        dump_ui(i)
        send_to_azure(f"window_dump_{i}.xml", args.session, args.azure, args.app)
        time.sleep(1)

    print("=== SCAN COMPLETED ===\n")

if __name__ == "__main__":
    main()