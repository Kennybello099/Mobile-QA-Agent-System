# mobile_qa.py
import subprocess
import time
import os
import warnings
import json
from typing import List, Dict
from PIL import Image
import google.generativeai as genai

warnings.filterwarnings("ignore", category=FutureWarning)

# ====================
# CONFIGURATION
# ====================
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment.")

genai.configure(api_key=GEMINI_API_KEY)

OBSIDIAN_PACKAGE = "md.obsidian"
ARTIFACTS_DIR = "artifacts"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ====================
# MODEL SETUP
# ====================
MODEL_NAME = "gemini-2.0-flash"  # Best for precise UI reasoning and coordinate accuracy

VISION_MODEL = genai.GenerativeModel(
    MODEL_NAME,
    generation_config=genai.GenerationConfig(
        temperature=0.1,
        max_output_tokens=1024,
    )
)

# ====================
# ADB HELPERS
# ====================
def adb(args):
    try:
        result = subprocess.run(["adb"] + args, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip() or "ADB error"
    except Exception as e:
        return False, str(e)

def device_check() -> bool:
    success, output = adb(["devices"])
    return success and "device" in output

def take_screenshot(path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, check=True)
        print(f"Screenshot saved: {path}")
        return True
    except Exception as e:
        print(f"Screenshot failed: {e}")
        return False

def tap(x: int, y: int) -> bool:
    success, _ = adb(["shell", "input", "tap", str(x), str(y)])
    print(f"Tap ({x}, {y}) → {'Success' if success else 'Failed'}")
    return success

def type_text(text: str) -> bool:
    if not text:
        return True
    escaped = text.replace(" ", "%s").replace('"', '\\"').replace("'", "\\'")
    success, _ = adb(["shell", "input", "text", escaped])
    print(f"Type: '{text}' → {'Success' if success else 'Failed'}")
    return success

def swipe(x1: int, y1: int, x2: int, y2: int, duration: int = 600) -> bool:
    success, _ = adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])
    print(f"Swipe ({x1},{y1})→({x2},{y2}) {duration}ms → {'Success' if success else 'Failed'}")
    return success

def press_key(key: str) -> bool:
    key_map = {"back": "4", "enter": "66", "home": "3"}
    code = key_map.get(key.lower())
    if not code:
        print(f"Unknown key: {key}")
        return False
    success, _ = adb(["shell", "input", "keyevent", code])
    print(f"Press {key} → {'Success' if success else 'Failed'}")
    return success

# ====================
# GEMINI VISION FUNCTIONS
# ====================
def get_next_action(goal: str, screenshot_path: str, history: List[str]) -> str:
    history_text = "\n".join(history[-8:]) if history else "None"

    prompt = f"""
You are an expert autonomous Android tester for Obsidian.

Goal: {goal}

Previous actions:
{history_text}

SCREEN INFO:
- Resolution: ~1080x2400
- X: 0=left → 1080=right
- Y: 0=top → 2400=bottom
- Center: (540, 1200)

Output EXACTLY one action:

tap|X|Y              → tap center of target
type|TEXT            → type this text
swipe|540|1800|540|800|600    → scroll up
swipe|540|800|540|1800|600    → scroll down
press|back
press|enter
done                 → only when goal is fully complete

Rules:
- Be extremely accurate with coordinates
- Never repeat failed taps
- Use swipe only if needed
- Output only the action string
"""

    try:
        img = Image.open(screenshot_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        response = VISION_MODEL.generate_content([prompt, img])
        action = response.text.strip()
        print(f"Next action: {action}")
        return action
    except Exception as e:
        print(f"Planning failed: {e}")
        return "done"

def verify_goal_completion(goal: str, screenshot_path: str) -> Dict:
    prompt = f"""
Strict QA verifier for Obsidian Android.

Goal: {goal}

Analyze screenshot and return ONLY valid JSON:

{{
  "completed": true/false,
  "pass": true/false,
  "reason": "clear evidence from screen"
}}

Rules:
- completed=true only if final state is clearly visible
- For vault creation: see vault open with file list
- For note creation: see title and body text
- For navigation: see target screen
- Be very strict and conservative
"""

    try:
        img = Image.open(screenshot_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        response = VISION_MODEL.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        text = response.text.strip()
        text = text.strip("```json").strip("```").strip()

        start = text.find('{')
        end = text.rfind('}') + 1
        json_str = text[start:end]
        result = json.loads(json_str)
        print(f"Verification: {result}")
        return result
    except Exception as e:
        print(f"Verification error: {e}")
        return {"completed": False, "pass": False, "reason": "Verification failed"}

# ====================
# AUTONOMOUS TEST LOOP
# ====================
def run_autonomous_test(test_id: str, goal: str, max_steps: int = 20) -> Dict:
    print(f"\nSTARTING TEST {test_id}: {goal}")

    if not device_check():
        return {"result": "FAIL", "reason": "No device connected"}

    test_dir = os.path.join(ARTIFACTS_DIR, test_id)
    os.makedirs(test_dir, exist_ok=True)

    # Launch Obsidian
    success, _ = adb(["shell", "monkey", "-p", OBSIDIAN_PACKAGE, "1"])
    if not success:
        print("Failed to launch Obsidian")
    time.sleep(10)

    history = []
    step = 0

    while step < max_steps:
        step += 1
        screenshot_path = os.path.join(test_dir, f"step_{step:02d}.png")
        take_screenshot(screenshot_path)

        # Verify goal
        verification = verify_goal_completion(goal, screenshot_path)
        if verification.get("completed"):
            result = "PASS" if verification.get("pass") else "FAIL"
            print(f"TEST {result}: {verification['reason']}")
            return {
                "result": result,
                "reason": verification["reason"],
                "artifacts": test_dir,
                "steps": step
            }

        # Plan next action
        action_str = get_next_action(goal, screenshot_path, history)
        if not action_str or action_str.strip().lower() == "done":
            print("Agent stopped (done or no action)")
            break

        # Parse and execute
        parts = [p.strip() for p in action_str.split("|")]
        success = False

        if parts[0] == "tap" and len(parts) == 3:
            success = tap(int(parts[1]), int(parts[2]))
        elif parts[0] == "type" and len(parts) == 2:
            success = type_text(parts[1])
        elif parts[0] == "swipe" and len(parts) == 5:
            success = swipe(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]))
        elif parts[0] == "press" and len(parts) == 2:
            success = press_key(parts[1])
        else:
            print(f"Invalid action: {action_str}")
            success = False

        status = "success" if success else "failed"
        history.append(f"{action_str} → {status}")
        print(f"Step {step}: {action_str} → {status}")

        time.sleep(5)  # Give UI time to respond

    # Final check
    final_verification = verify_goal_completion(goal, screenshot_path)
    if final_verification.get("completed"):
        return {
            "result": "PASS" if final_verification.get("pass") else "FAIL",
            "reason": final_verification["reason"],
            "artifacts": test_dir,
            "steps": step
        }

    return {
        "result": "FAIL",
        "reason": "Max steps reached without completion",
        "artifacts": test_dir,
        "steps": step
    }

# ====================
# TESTS
# ====================
if __name__ == "__main__":
    TESTS = [
        ("T1", "Create a new vault named 'InternVault'"),
        ("T2", "Create a new note titled 'Meeting Notes' with body 'Daily Standup'"),
        ("T3", "Open Settings and go to the Appearance section"),
        ("T4", "Open a note, open the three-dot menu, scroll down, and confirm 'Print to PDF' option is visible"),
    ]

    for tid, goal in TESTS:
        result = run_autonomous_test(tid, goal)
        print(f"{tid} → {result['result']} | {result.get('reason', '')}")
        print(f"   Artifacts: {result['artifacts']}\n")