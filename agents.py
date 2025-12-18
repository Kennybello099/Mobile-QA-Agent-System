import json
from gemini_helper import analyze_image_with_prompt
from adb_helper import tap, type_text, swipe, keyevent, launch_app, take_screenshot


class Planner:
    def __init__(self):
        self.prompt_template = """
You are a mobile QA agent. Decide the next action the AGENT must perform.
Do NOT explain. Output ONLY one action string:

- launch|md.obsidian
- tap|X|Y
- type|TEXT
- swipe|X1|Y1|X2|Y2|DURATION
- press|home/back/enter
- shot|artifacts/{test_id}/step_{step}.png
- DONE
"""

    def decide_next_action(self, test_case, screenshot_path, test_id="T", step=1):
        prompt = self.prompt_template.format(test_case=test_case, test_id=test_id, step=step)
        response = analyze_image_with_prompt(screenshot_path, prompt)
        if not isinstance(response, str):
            return "DONE"
        return response.strip()


class Supervisor:
    def __init__(self):
        self.prompt_template = """
You are a mobile QA supervisor. Verify if the AGENT advanced along this sequence:

1) Welcome screen with “Create a vault”
2) Sync prompt with “Continue without sync”
3) Vault naming screen (text field + “Create a vault” button)
4) Inside vault (file explorer or editor)

Return ONLY a JSON object, no code fences, no extra text. Decide dynamically based on the screenshot:

- If the expected state is reached: { "completed": true, "pass": true, "reason": "<describe evidence of success>" }
- If the expected state is reached but incorrect: { "completed": true, "pass": false, "failure_type": "<ElementNotFound|NavigationTimeout|FocusError>", "reason": "<describe evidence of failure>" }
- If the sequence is not complete: { "completed": false, "next_expected_state": "<welcome|sync|naming|inside_vault>" }
"""

    def _parse_json(self, response: str):
        try:
            return json.loads(response.strip())
        except Exception:
            start, end = response.find('{'), response.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(response[start:end+1])
                except Exception:
                    pass
        return {"completed": False, "next_expected_state": "Unparseable response"}

    def verify_state(self, test_case, screenshot_path):
        # Appearance test
        if "Appearance" in test_case and "Red" in test_case:
            prompt = """
You are a mobile QA supervisor. Verify if the 'Appearance' tab icon is red.
Return ONLY a raw JSON object, no code fences, no extra text. Decide dynamically:

- If red: { "completed": true, "pass": true, "reason": "Appearance tab icon is red" }
- If not red: { "completed": true, "pass": false, "failure_type": "ColorMismatch", "reason": "Appearance tab icon is <actual color>" }
"""
            response = analyze_image_with_prompt(screenshot_path, prompt)
            if not isinstance(response, str):
                return {"completed": False, "next_expected_state": "Invalid response type"}
            return self._parse_json(response)

        # Print to PDF test
        if "Print to PDF" in test_case:
            prompt = """
You are a mobile QA supervisor. Verify if the overflow menu contains a button labeled 'Print to PDF'.
Return ONLY a raw JSON object, no code fences, no extra text. Decide dynamically:

- If visible: { "completed": true, "pass": true, "reason": "'Print to PDF' button is visible in the menu" }
- If missing: { "completed": true, "pass": false, "failure_type": "ElementNotFound", "reason": "'Print to PDF' button is missing from the menu" }
"""
            response = analyze_image_with_prompt(screenshot_path, prompt)
            if not isinstance(response, str):
                return {"completed": False, "next_expected_state": "Invalid response type"}
            return self._parse_json(response)

        # Default vault/note verification
        prompt = f"{self.prompt_template}\nTest case: {test_case}"
        response = analyze_image_with_prompt(screenshot_path, prompt)
        if not isinstance(response, str):
            return {"completed": False, "next_expected_state": "Invalid response type"}
        return self._parse_json(response)


class Executor:
    def __init__(self):
        self.actions = {
            'tap': tap,
            'type': type_text,
            'swipe': swipe,
            'keyevent': keyevent,
            'launch': launch_app,
            'shot': take_screenshot,
        }
        self.keymap = {"enter": "66", "back": "4", "home": "3"}

    def execute(self, action_str):
        parts = action_str.split("|")
        action = parts[0].lower()
        params = parts[1:]

        if action == "tap":
            x, y = map(int, params)
            return tap(x, y)
        elif action == "swipe":
            x1, y1, x2, y2, duration = map(int, params)
            return swipe(x1, y1, x2, y2, duration)
        elif action in self.actions:
            return self.actions[action](*params)
        elif action == "done":
            return True
        elif action == "press":
            keycode = self.keymap.get(params[0].lower())
            if keycode:
                return keyevent(str(keycode))
            raise ValueError(f"Unknown press key: {params[0]}")
        else:
            raise ValueError(f"Unknown action: {action}")