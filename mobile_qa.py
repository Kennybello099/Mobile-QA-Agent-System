# mobile_qa.py
import subprocess
import time
import os
import warnings
from typing import Optional, Tuple, Dict
from PIL import Image
import google.generativeai as genai

# ====================
# CONFIGURATION
# ====================
warnings.filterwarnings("ignore", category=FutureWarning)  # Suppress noisy warnings

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
EMULATOR_NAME = os.getenv('AVD_NAME', "Pixel_9_Pro_API_36")
OBSIDIAN_PACKAGE = "md.obsidian"

SCREENSHOT_FILE = "current_screen.png"

# ====================
# GEMINI MODEL RESOLUTION
# ====================
def resolve_model(preferred: str, fallbacks: Tuple[str, ...] = ("models/gemini-pro-latest",)) -> genai.GenerativeModel:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    genai.configure(api_key=GEMINI_API_KEY)

    try:
        return genai.GenerativeModel(preferred)
    except Exception:
        pass

    for name in fallbacks:
        try:
            return genai.GenerativeModel(name)
        except Exception:
            continue

    models = genai.list_models()
    for m in models:
        if hasattr(m, "supported_generation_methods") and "generateContent" in getattr(m, "supported_generation_methods", []):
            return genai.GenerativeModel(m.name)

    raise RuntimeError("No compatible Gemini model available.")

def get_text_model() -> genai.GenerativeModel:
    return resolve_model("models/gemini-pro-latest")

def get_vision_model() -> genai.GenerativeModel:
    try:
        return resolve_model("models/gemini-pro-latest")
    except Exception:
        return get_text_model()

# ====================
# ADB HELPERS
# ====================
def adb(args) -> Tuple[bool, str]:
    try:
        result = subprocess.run(["adb"] + args, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except Exception as e:
        return False, str(e)

def device_check() -> bool:
    ok, out = adb(["devices"])
    if not ok:
        print(f"❌ ADB devices failed: {out}")
        return False
    lines = [l for l in out.splitlines() if l and not l.lower().startswith("list of devices")]
    return len(lines) > 0

def take_screenshot(filename: str = SCREENSHOT_FILE) -> bool:
    try:
        with open(filename, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, check=True)
        print(f"📸 Screenshot saved: {filename}")
        return True
    except Exception as e:
        print(f"❌ Screenshot failed: {e}")
        return False

def tap_screen(x: int, y: int) -> bool:
    ok, _ = adb(["shell", "input", "tap", str(x), str(y)])
    print(f"🛠 Tap at ({x},{y}) {'OK' if ok else 'FAIL'}")
    return ok

def type_text(text: str) -> bool:
    adb_text = text.replace(" ", "%s")
    ok, _ = adb(["shell", "input", "text", adb_text])
    print(f"⌨️ Type '{text}' {'OK' if ok else 'FAIL'}")
    return ok

KEYEVENT_MAP = {"back": "4", "home": "3", "enter": "66", "tab": "61", "escape": "111"}

def press_key(key: str) -> bool:
    code = KEYEVENT_MAP.get(key.lower())
    if not code:
        print(f"⚠️ Unsupported key: {key}")
        return False
    ok, _ = adb(["shell", "input", "keyevent", code])
    print(f"🔘 Press '{key}' {'OK' if ok else 'FAIL'}")
    return ok

# ====================
# GEMINI INTERACTION
# ====================
def ask_gemini_action_text_only(model: genai.GenerativeModel, test_case: str) -> Optional[str]:
    prompt = f"""
You are a mobile QA assistant for Android UI tests.

CURRENT TEST: {test_case}

Return ONE next action. Choose from:
- tap|X|Y
- type|TEXT
- press|KEY  (KEY ∈ {{home, back, enter}})

Only return the action string.
"""
    try:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", "").strip()
        print(f"🤖 Gemini (text-only): {text}")
        return text or None
    except Exception as e:
        print(f"❌ Gemini text-only error: {e}")
        return None

def ask_gemini_action_with_image(model: genai.GenerativeModel, test_case: str, screenshot_path: str) -> Optional[str]:
    try:
        img = Image.open(screenshot_path)
    except Exception as e:
        print(f"❌ Could not open screenshot: {e}")
        return None

    prompt = f"""
You are a mobile QA assistant. Look at this Android screenshot.

CURRENT TEST: {test_case}

Return ONE next action in EXACT format:
- tap|X|Y
- type|TEXT
- press|KEY (KEY ∈ {{home, back, enter}})
"""
    try:
        resp = model.generate_content([{"text": prompt}, img])
        text = getattr(resp, "text", None)
        if not text and getattr(resp, "candidates", None):
            parts = resp.candidates[0].content.parts
            if parts and hasattr(parts[0], "text"):
                text = parts[0].text
        action = text.strip() if text else None
        print(f"🤖 Gemini (vision): {action}")
        return action
    except Exception as e:
        print(f"❌ Gemini vision error: {e}")
        return None

# ====================
# ACTION PARSING & EXECUTION
# ====================
def parse_action(action_str: str) -> Optional[Dict]:
    if not action_str:
        return None
    parts = [p.strip() for p in action_str.split("|")]
    if not parts:
        return None
    action = parts[0].lower()
    if action == "tap" and len(parts) == 3:
        try:
            return {"type": "tap", "x": int(parts[1]), "y": int(parts[2])}
        except ValueError:
            return None
    if action == "type" and len(parts) == 2:
        return {"type": "type", "text": parts[1]}
    if action == "press" and len(parts) == 2:
        return {"type": "press", "key": parts[1].lower()}
    return None

def execute_action(act: Dict) -> bool:
    if not act or "type" not in act:
        print("⚠️ Invalid action payload.")
        return False
    if act["type"] == "tap":
        return tap_screen(act["x"], act["y"])
    if act["type"] == "type":
        return type_text(act["text"])
    if act["type"] == "press":
        return press_key(act["key"])
    print(f"⚠️ Unknown action type: {act['type']}")
    return False

# ====================
# TEST LOOP
# ====================
def run_test(test_case: str) -> str:
    print(f"\n🚀 STARTING TEST: {test_case}")

    if not device_check():
        return "FAIL - No emulator/device connected"

    vision_model = None
    try:
        vision_model = get_vision_model()
    except Exception:
        pass
    text_model = get_text_model()

    if not take_screenshot():
        return "FAIL - Cannot take screenshot"

    action_str = None
    if vision_model:
        action_str = ask_gemini_action_with_image(vision_model, test_case, SCREENSHOT_FILE)
    if not action_str:
        action_str = ask_gemini_action_text_only(text_model, test_case)
    if not action_str:
        return "FAIL - No action from Gemini"

    act = parse_action(action_str)
    if not act:
        print(f"⚠️ Could not parse action: {action_str}")
        return "FAIL - Bad action format"

    if not execute_action(act):
        return "FAIL - Action execution failed"

    time.sleep(2)
    take_screenshot()

    return "IN_PROGRESS"

# ====================
# MAIN
# ====================
TEST_CASES = [
    "Open Obsidian app",
    "Create a new note called 'Test Note'",
]

if __name__ == "__main__":
    print("🚀 Mobile QA Agent Starting...")
    print("Make sure your Android emulator is running!")
    for case in TEST_CASES:
        result = run_test(case)
        print(f"\n🏁 Test Result for '{case}': {result}")