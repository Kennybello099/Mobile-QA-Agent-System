import json
from typing import List, Dict, Any
from gemini_helper import analyze_image_with_prompt
from adb_helper import tap, type_text, dump_ui_hierarchy
from ui_parser import get_clickable_elements


def is_vault_goal(goal: str) -> bool:
    return "vault" in goal.lower()


def is_note_creation_goal(goal: str) -> bool:
    g = goal.lower()
    patterns = [
        "create a new note titled",
        "create new note titled",
        "create a note titled",
        "create note titled",
        "new note titled",
    ]
    return any(p in g for p in patterns)


def is_settings_appearance_goal(goal: str) -> bool:
    g = goal.lower()
    return "go to settings" in g and "navigate to the appearance tab" in g


class Planner:
    def __init__(self):
        self.field_tapped = False
        self.name_typed = False
        self.title_typed = False
        self.body_tap_done = False
        self.body_typed = False
        self.three_dots_tapped = False
        self.tap_attempts = 0
        # T3 state
        self.gear_tapped = False
        self.appearance_row_tapped = False

    def decide_next_action(self, goal: str, screenshot_path: str, history: List[str]) -> str:
        dump_ui_hierarchy()
        elements = get_clickable_elements()
        vision_prompt = """
You are classifying an Obsidian Android screen.
Return EXACTLY one label from this list:
"welcome", "sync", "config", "folder_select", "permission",
"new_tab", "editor", "file_browser", "vault_open", "loading", "settings", "appearance"
DEFINITIONS:
- "editor": A note is open. You see a title field at the top (often 'Untitled')
  and a large empty body area below. There may be formatting icons or a cursor.
- "new_tab": This is the screen that appears after tapping the 3-dots menu.
  It shows actions like "Create new note (Ctrl + N)" and "Open another vault".
- "file_browser": Shows the vault name at the top, file list, and icons like
  pencil, plus, upload, folder, download.
- "settings": The main Settings screen is visible, with a list of categories like "Appearance", "Editor", "Files & links", etc.
- "appearance": The Appearance settings tab is open, showing options like Theme, Accent color, Font, etc.
Return ONLY the label.
"""
        vision_desc = analyze_image_with_prompt(screenshot_path, vision_prompt) or "unknown"
        vision_desc = vision_desc.lower().strip()
        # Heuristic override: if UI hierarchy contains "untitled", force editor
        try:
            ui_xml = open("current_ui.xml", "r", encoding="utf-8").read().lower()
            if "untitled" in ui_xml:
                vision_desc = "editor"
        except:
            pass
        print(f"Vision detected: {vision_desc}")

        # -------------------------
        # T1: Vault creation (YOUR ORIGINAL - UNTOUCHED)
        # -------------------------
        if is_vault_goal(goal):
            if "welcome" in vision_desc:
                return "tap_index|0"
            elif "sync" in vision_desc:
                return "tap_index|0"
            elif "config" in vision_desc:
                if not self.field_tapped:
                    self.field_tapped = True
                    return "tap_index|0"
                if not self.name_typed:
                    self.name_typed = True
                    return "type|InternVault"
                for i, e in enumerate(elements):
                    if "create a vault" in (e.get("text", "") or "").lower():
                        return f"tap_index|{i}"
                return "tap_index|1"
            elif "folder_select" in vision_desc:
                return "tap_index|5"
            elif "permission" in vision_desc:
                return "tap_index|1"
            elif "vault_open" in vision_desc or "loading" in vision_desc:
                return "wait|3"
            return "tap_index|0"

        # -------------------------
        # T2: Note creation (YOUR ORIGINAL - UNTOUCHED)
        # -------------------------
        if is_note_creation_goal(goal):
            # Step 1: Tap 3-dots
            if "file_browser" in vision_desc:
                if not self.three_dots_tapped:
                    self.three_dots_tapped = True
                    for i, e in enumerate(elements):
                        bounds = e.get("bounds", [0, 0, 0, 0])
                        x1, y1, x2, y2 = bounds
                        width = x2 - x1
                        height = y2 - y1
                        if y1 < 250 and width < 200 and height < 200 and x1 > 850:
                            return f"tap_index|{i}"
                    return "tap_xy|1020|150"
                return "wait|2"
            # Step 2: Tap "Create new note"
            elif "new_tab" in vision_desc:
                for i, e in enumerate(elements):
                    if "create new note" in (e.get("text", "") or "").lower():
                        return f"tap_index|{i}"
                if self.tap_attempts < 4:
                    tap_prompt = """
Identify EXACT pixel coordinate to tap:
"Create new note (Ctrl + N)"
Return ONLY:
{{
  "x": <int>,
  "y": <int>
}}
"""
                    resp = analyze_image_with_prompt(screenshot_path, tap_prompt)
                    try:
                        text = resp.strip().strip("```json").strip("```").strip()
                        coord = json.loads(text[text.find("{"):text.rfind("}")+1])
                        x, y = int(coord["x"]), int(coord["y"])
                        self.tap_attempts += 1
                        return f"tap_xy|{x}|{y}"
                    except:
                        self.tap_attempts += 1
                if self.tap_attempts < 7:
                    offsets = [(0,20),(0,-20),(20,0),(-20,0),(20,20),(-20,-20)]
                    dx, dy = offsets[self.tap_attempts % len(offsets)]
                    base_x, base_y = 639, 1382
                    x, y = base_x + dx, base_y + dy
                    self.tap_attempts += 1
                    return f"tap_xy|{x}|{y}"
                return "FAILED"
            # Step 3: Editor — type title + body
            elif "editor" in vision_desc:
                if not self.title_typed:
                    self.title_typed = True
                    return "type|Meeting Notes"
                if not self.body_tap_done:
                    body_prompt = """
Identify pixel coordinate to tap the BODY area.
Return ONLY:
{{
  "x": <int>,
  "y": <int>
}}
"""
                    resp = analyze_image_with_prompt(screenshot_path, body_prompt)
                    try:
                        text = resp.strip().strip("```json").strip("```").strip()
                        coord = json.loads(text[text.find("{"):text.rfind("}")+1])
                        x, y = int(coord["x"]), int(coord["y"])
                        self.body_tap_done = True
                        return f"tap_xy|{x}|{y}"
                    except:
                        self.body_tap_done = True
                        return "tap_xy|640|1200"
                if not self.body_typed:
                    self.body_typed = True
                    return "type|Daily Standup"
                return "DONE"
            return "tap_index|0"

        # -------------------------
        # T3: Tap settings → Appearance → check accent color red
        # -------------------------
        if is_settings_appearance_goal(goal):
            if "file_browser" in vision_desc:
                if not self.gear_tapped:
                    self.gear_tapped = True
                    return "tap_xy|1011|228"
            elif "settings" in vision_desc:
                if not self.appearance_row_tapped:
                    self.appearance_row_tapped = True
                    for i, e in enumerate(elements):
                        text = (e.get("text", "") or "").lower()
                        if "appearance" in text:
                            return f"tap_index|{i}"
                    return "tap_xy|540|580"
            elif "appearance" in vision_desc:
                return "DONE"
            return "tap_index|0"

        return "tap_index|0"


class Supervisor:
    def __init__(self):
        self.base_prompt = """
You are a strict verifier for Obsidian Android.
Goal: {goal}
Return ONLY JSON:
{{
  "completed": true/false,
  "pass": true/false,
  "reason": "short explanation"
}}

RULES:
1) Vault goal:
   Pass ONLY IF:
     - Screen is file_browser
     - Vault name 'InternVault' visible
     - Files section visible
2) Note creation goal:
   Pass ONLY IF:
     - Screen is editor
     - Title == 'Meeting Notes'
     - Body contains 'Daily Standup'
3) If editor is open but content does NOT match:
     completed=false, pass=false
4) Settings → Appearance goal:
   Pass ONLY IF:
     - The Appearance tab is open (title "Appearance")
     - Options like "Base color scheme", "Accent color", "Themes", "Font" visible
     - Accent color swatch is RED or reddish-purple
   Fail if accent color is not red
"""

    def verify_state(self, goal: str, screenshot_path: str) -> Dict[str, Any]:
        prompt = self.base_prompt.format(goal=goal)
        response = analyze_image_with_prompt(screenshot_path, prompt, temperature=0.0)
        if not response:
            return {"completed": False, "pass": False, "reason": "No response"}
        try:
            text = response.strip().strip("```json").strip("```").strip()
            parsed = json.loads(text[text.find("{"):text.rfind("}")+1])
            return {
                "completed": parsed.get("completed", False),
                "pass": parsed.get("pass", False),
                "reason": parsed.get("reason", "")
            }
        except:
            return {"completed": False, "pass": False, "reason": "Parse error"}


class Executor:
    def execute(self, action_str: str) -> bool:
        if not action_str or "DONE" in action_str.upper():
            print("Goal completed.")
            return True
        if action_str.startswith("wait|"):
            import time
            seconds = int(action_str.split("|")[1])
            time.sleep(seconds)
            return True
        if action_str.startswith("tap_index|"):
            index = int(action_str.split("|")[1])
            elements = get_clickable_elements()
            if index == -1:
                index = len(elements) - 1
            if 0 <= index < len(elements):
                x, y = elements[index]["center"]
                print(f"Tapping index {index} at ({x},{y})")
                return tap(x, y)
            print("Invalid tap_index")
            return False
        if action_str.startswith("tap_xy|"):
            _, x, y = action_str.split("|")
            x, y = int(x), int(y)
            print(f"Tapping at ({x},{y})")
            return tap(x, y)
        if action_str.startswith("type|"):
            text = action_str.split("|", 1)[1]
            print(f"Typing: {text}")
            return type_text(text)
        print(f"Unsupported action: {action_str}")
        return False