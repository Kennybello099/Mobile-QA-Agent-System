# adb_helper.py
import subprocess
import os
from typing import Optional

def _run_adb(cmd: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["adb"] + cmd,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except FileNotFoundError:
        return False, "ADB not found in PATH"
    except Exception as e:
        return False, f"ADB exception: {str(e)}"

def device_check() -> bool:
    success, output = _run_adb(["devices"])
    if not success:
        print(f"ADB devices failed: {output}")
        return False
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return any("device" in line and not line.endswith("offline") for line in lines)

def tap(x: int, y: int) -> bool:
    x, y = int(x), int(y)
    success, output = _run_adb(["shell", "input", "tap", str(x), str(y)])
    if success:
        print(f"Tap ({x}, {y})")
        return True
    else:
        print(f"Failed to tap ({x}, {y}): {output}")
        return False

def type_text(text: str) -> bool:
    if not text:
        return True
    safe_text = (text
                 .replace("\\", "\\\\")
                 .replace(" ", "%s")
                 .replace("&", "\\&")
                 .replace("'", "\\'")
                 .replace('"', '\\"')
                 .replace(";", "\\;")
                 .replace("(", "\\(")
                 .replace(")", "\\)"))
    success, output = _run_adb(["shell", "input", "text", safe_text])
    if success:
        print(f"Typed: {text}")
        return True
    else:
        print(f"Failed to type '{text}': {output}")
        return False

def swipe(x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
    coords = [int(x1), int(y1), int(x2), int(y2), int(duration)]
    success, output = _run_adb(["shell", "input", "swipe", *map(str, coords)])
    if success:
        print(f"Swipe {coords[:-1]} over {duration}ms")
        return True
    else:
        print(f"Swipe failed: {output}")
        return False

def keyevent(keycode: str) -> bool:
    success, output = _run_adb(["shell", "input", "keyevent", str(keycode)])
    key_names = {"3": "HOME", "4": "BACK", "66": "ENTER"}
    name = key_names.get(str(keycode), keycode)
    if success:
        print(f"Keyevent: {name}")
        return True
    else:
        print(f"Keyevent {name} failed: {output}")
        return False

def press_back() -> bool:
    return keyevent("4")

def press_enter() -> bool:
    return keyevent("66")

def launch_app(package_name: str) -> bool:
    success, output = _run_adb([
        "shell", "monkey",
        "-p", package_name,
        "-c", "android.intent.category.LAUNCHER",
        "1"
    ])
    if success:
        print(f"Launched: {package_name}")
        return True
    success2, _ = _run_adb(["shell", "pidof", package_name])
    if success2:
        print(f"Launched (fallback): {package_name}")
        return True
    print(f"Failed to launch {package_name}: {output}")
    return False

def take_screenshot(path: str) -> bool:
    if not path:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "wb") as f:
            subprocess.run(
                ["adb", "exec-out", "screencap", "-p"],
                stdout=f,
                stderr=subprocess.PIPE,
                check=True
            )
        print(f"Screenshot saved: {path}")
        return True
    except Exception as e:
        print(f"Screenshot exception: {e}")
        return False

# NEW: Dump UI hierarchy
def dump_ui_hierarchy(device_path: str = "/sdcard/ui.xml", local_path: str = "current_ui.xml") -> Optional[str]:
    """Dump UI hierarchy via uiautomator and pull to local."""
    try:
        # Dump on device
        success, _ = _run_adb(["shell", "uiautomator", "dump", device_path])
        if not success:
            print("UI dump failed on device")
            return None
        # Pull to local
        success, _ = _run_adb(["pull", device_path, local_path])
        if success and os.path.exists(local_path):
            print(f"UI hierarchy saved: {local_path}")
            return local_path
        return None
    except Exception as e:
        print(f"UI hierarchy dump failed: {e}")
        return None