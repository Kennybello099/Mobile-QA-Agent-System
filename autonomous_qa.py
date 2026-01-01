# autonomous_qa.py
import os
import time
from agents import Planner, Supervisor, Executor
from adb_helper import take_screenshot, device_check, launch_app, _run_adb


def is_obsidian_running() -> bool:
    success, output = _run_adb(["shell", "pidof", "md.obsidian"])
    return success and output.strip() != ""


def should_relaunch() -> bool:
    return not is_obsidian_running()


def run_test(test_id: str, goal: str, max_steps: int = 20):
    print(f"\nSTARTING {test_id}: {goal}")

    if not device_check():
        print("No device found")
        return

    artifacts_dir = f"artifacts/{test_id}"
    os.makedirs(artifacts_dir, exist_ok=True)

    planner = Planner()
    supervisor = Supervisor()
    executor = Executor()

    history = []
    step = 0

    # Relaunch only if Obsidian is NOT running
    if should_relaunch():
        print("Obsidian not running → launching...")
        launch_app("md.obsidian")
        time.sleep(10)
    else:
        print("Obsidian already running → no relaunch.")

    while step < max_steps:
        step += 1
        screenshot_path = f"{artifacts_dir}/step_{step:02d}.png"
        take_screenshot(screenshot_path)

        # Check if done
        verification = supervisor.verify_state(goal, screenshot_path)
        if verification.get("completed"):
            result = "PASS" if verification.get("pass") else "FAIL"
            print(f"RESULT: {result} | {verification['reason']}")
            return

        # Plan & execute
        action = planner.decide_next_action(goal, screenshot_path, history)
        success = executor.execute(action)

        status = "success" if success else "failed"
        history.append(f"{action} → {status}")
        print(f"Step {step}: {action} → {status}")

        if action.lower() == "done":
            break

        time.sleep(3)

    print("Max steps reached")


if __name__ == "__main__":
    tests = [
        ("T1", "Create a new vault named 'InternVault' and open it"),
        ("T2", "Create a new note titled 'Meeting Notes' with body 'Daily standup'"),
        ("T3", "Go to Settings > Appearance and confirm the tab is visible"),
        ("T4", "Open a note, tap three-dot menu, scroll if needed, and confirm 'Print to PDF' is visible"),
    ]

    for tid, goal in tests:
        run_test(tid, goal)