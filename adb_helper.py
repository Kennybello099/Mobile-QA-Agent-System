import subprocess

def tap(x, y):
    x, y = int(x), int(y)
    subprocess.run(
        ["adb", "shell", "input", "tap", str(x), str(y)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

def type_text(text):
    safe_text = text.replace(" ", "%s").replace("&", "\\&").replace("'", "\\'")
    subprocess.run(
        ["adb", "shell", "input", "text", safe_text],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

def swipe(x1, y1, x2, y2, duration=300):
    x1, y1, x2, y2, duration = map(int, [x1, y1, x2, y2, duration])
    subprocess.run(
        ["adb", "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

def keyevent(key):
    subprocess.run(
        ["adb", "shell", "input", "keyevent", str(key)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

def launch_app(package_name):
    subprocess.run(
        ["adb", "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

def take_screenshot(path):
    with open(path, "wb") as f:
        subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            stdout=f, stderr=subprocess.DEVNULL, check=True
        )

def device_check():
    try:
        output = subprocess.check_output(["adb", "devices"], stderr=subprocess.DEVNULL).decode()
        return "device" in output
    except Exception:
        return False