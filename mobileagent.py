# mobileagent.py
import os
import time
import warnings
from adb_helper import take_screenshot, device_check, launch_app, dump_ui_hierarchy, _run_adb
from agents import Planner, Supervisor, Executor
from gemini_helper import analyze_image_with_prompt

warnings.filterwarnings("ignore", category=FutureWarning)


def is_obsidian_running() -> bool:
    success, output = _run_adb(["shell", "pidof", "md.obsidian"])
    return success and output.strip() != ""


class MobileQAAgent:
    def __init__(self):
        self.planner = Planner()
        self.supervisor = Supervisor()
        self.executor = Executor()

    def should_relaunch(self) -> bool:
        # Relaunch ONLY if Obsidian is NOT running
        return not is_obsidian_running()

    def run_test(self, test_id: str, test_goal: str, max_steps: int = 20):
        print(f"\nSTARTING TEST {test_id}: {test_goal}")

        if not device_check():
            return {"result": "FAIL", "reason": "No emulator/device connected"}

        artifacts_dir = f"artifacts/{test_id}"
        os.makedirs(artifacts_dir, exist_ok=True)

        # Decide whether to relaunch based on process state
        if self.should_relaunch():
            print("Obsidian not running → launching...")
            if not launch_app("md.obsidian"):
                return {"result": "FAIL", "reason": "Failed to launch Obsidian"}
            time.sleep(10)
        else:
            print("Obsidian already running → no relaunch.")

        history = []
        step = 0

        while step < max_steps:
            step += 1
            screenshot_path = f"{artifacts_dir}/step_{step:02d}.png"
            take_screenshot(screenshot_path)
            print(f"Step {step}: Screenshot saved → {screenshot_path}")

            dump_ui_hierarchy()

            # 1. Verify goal
            verification = self.supervisor.verify_state(test_goal, screenshot_path)
            if verification.get("completed"):
                result = "PASS" if verification.get("pass") else "FAIL"
                reason = verification.get("reason", "Goal achieved")
                print(f"TEST {result}: {reason}")
                return {
                    "result": result,
                    "reason": reason,
                    "artifacts": artifacts_dir,
                    "steps_taken": step
                }

            # 2. Plan
            action = self.planner.decide_next_action(
                goal=test_goal,
                screenshot_path=screenshot_path,
                history=history
            )

            if not action or action.strip().lower() == "done":
                print("Agent stopped (DONE or no action)")
                break

            print(f"Planned action: {action}")

            # 3. Execute
            success = self.executor.execute(action)
            status = "success" if success else "failed"
            history.append(f"{action} → {status}")
            print(f"Executed → {status}")

            time.sleep(6)

        return {
            "result": "FAIL",
            "reason": f"Max steps ({max_steps}) reached",
            "artifacts": artifacts_dir,
            "steps_taken": step
        }


if __name__ == "__main__":
    agent = MobileQAAgent()

    TESTS = [
        ("T1", "Create a new vault named 'InternVault' and open it"),
        ("T2", "Create a new note titled 'Meeting Notes' with body 'Daily Standup'"),
        ("T3", "Go to Settings and navigate to the Appearance tab"),
        ("T4", "Open any note, tap the three-dot menu, scroll down, and confirm 'Print to PDF' option is visible"),
    ]

    for test_id, goal in TESTS:
        result = agent.run_test(test_id, goal)
        print(f"{test_id} → {result['result']} | {result.get('reason', '')}")
        print(f"   Artifacts: {result['artifacts']}\n")