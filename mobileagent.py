import os
import time
import warnings
from adb_helper import take_screenshot, device_check, type_text
from agents import Planner, Supervisor, Executor

# Suppress noisy warnings (like google.api_core FutureWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

class MobileQAAgent:
    def __init__(self):
        self.planner = Planner()
        self.supervisor = Supervisor()
        self.executor = Executor()

    def run_test(self, test_id, test_case, flow="vault", max_steps=12):
        print(f"\n🚀 STARTING TEST {test_id}: {test_case}")
        if not device_check():
            return {"result": "FAIL", "reason": "No emulator/device connected"}

        artifacts_dir = f"artifacts/{test_id}"
        os.makedirs(artifacts_dir, exist_ok=True)

        coords = {
            "create_vault_button": (671, 1269),
            "continue_without_sync": (542, 1515),
            "vault_name_field": (540, 800),
            "create_vault_confirm": (540, 2250),
            "use_this_folder": (640, 2715),
            "allow_file_access": (1058, 1647),
            "new_note_button": (574, 1359),
            "note_title_field": (540, 400),
            "note_body_field": (540, 800),
            "menu_button": (100, 227),
            "settings_button": (1013, 227),
            "appearance_tab": (184, 1048),
            "meeting_notes_file": (304, 748),
            "three_dot_menu": (1178, 228),
            "close_button": (205, 1231),
        }

        # Launch app
        self.executor.execute("launch|md.obsidian")
        time.sleep(6)

        if flow == "vault":
            self.executor.execute(f"tap|{coords['create_vault_button'][0]}|{coords['create_vault_button'][1]}")
            time.sleep(5)
            self.executor.execute(f"tap|{coords['continue_without_sync'][0]}|{coords['continue_without_sync'][1]}")
            time.sleep(5)
            self.executor.execute(f"tap|{coords['vault_name_field'][0]}|{coords['vault_name_field'][1]}")
            type_text("InternVault")
            self.executor.execute("press|enter")
            time.sleep(2)
            self.executor.execute(f"tap|{coords['create_vault_confirm'][0]}|{coords['create_vault_confirm'][1]}")
            time.sleep(6)
            self.executor.execute(f"tap|{coords['use_this_folder'][0]}|{coords['use_this_folder'][1]}")
            time.sleep(6)
            self.executor.execute(f"tap|{coords['allow_file_access'][0]}|{coords['allow_file_access'][1]}")
            time.sleep(6)

        elif flow == "note":
            self.executor.execute(f"tap|{coords['new_note_button'][0]}|{coords['new_note_button'][1]}")
            time.sleep(3)
            self.executor.execute(f"tap|{coords['note_title_field'][0]}|{coords['note_title_field'][1]}")
            type_text("Meeting Notes")
            self.executor.execute("press|enter")
            time.sleep(2)
            self.executor.execute(f"tap|{coords['note_body_field'][0]}|{coords['note_body_field'][1]}")
            type_text("Daily Standup")
            time.sleep(2)

        elif flow == "appearance":
            self.executor.execute(f"tap|{coords['menu_button'][0]}|{coords['menu_button'][1]}")
            time.sleep(3)
            self.executor.execute(f"tap|{coords['settings_button'][0]}|{coords['settings_button'][1]}")
            time.sleep(3)
            self.executor.execute(f"tap|{coords['appearance_tab'][0]}|{coords['appearance_tab'][1]}")
            time.sleep(3)

        elif flow == "print_to_pdf":
            self.executor.execute("press|back")
            time.sleep(1)
            self.executor.execute("press|back")
            time.sleep(1)
            self.executor.execute(f"tap|{coords['meeting_notes_file'][0]}|{coords['meeting_notes_file'][1]}")
            time.sleep(2)
            self.executor.execute("tap|540|800")
            time.sleep(1)
            self.executor.execute(f"tap|{coords['three_dot_menu'][0]}|{coords['three_dot_menu'][1]}")
            time.sleep(2)
            take_screenshot(f"{artifacts_dir}/menu_open.png")
            self.executor.execute("swipe|600|1600|600|800|800")
            time.sleep(2)
            take_screenshot(f"{artifacts_dir}/menu_scrolled.png")
            self.executor.execute("swipe|600|800|600|1600|800")
            time.sleep(2)
            self.executor.execute(f"tap|{coords['close_button'][0]}|{coords['close_button'][1]}")
            time.sleep(2)
            take_screenshot(f"{artifacts_dir}/menu_closed.png")

        # Final screenshots
        take_screenshot(f"{artifacts_dir}/final_1.png")
        time.sleep(2)
        take_screenshot(f"{artifacts_dir}/final_2.png")

        screenshots_to_check = ["final_2.png", "final_1.png"]
        if flow == "print_to_pdf":
            screenshots_to_check = ["menu_closed.png", "menu_scrolled.png", "menu_open.png"] + screenshots_to_check

        for shot_name in screenshots_to_check:
            shot_path = f"{artifacts_dir}/{shot_name}"
            if not os.path.exists(shot_path):
                continue
            verification = self.supervisor.verify_state(test_case, shot_path)
            # Supervisor now decides pass/fail dynamically
            if verification.get("completed"):
                return {
                    "result": "PASS" if verification.get("pass") else "FAIL",
                    "reason": verification.get("reason", ""),
                    "artifacts": artifacts_dir
                }

        return {"result": "FAIL", "reason": "Condition not met", "artifacts": artifacts_dir}


if __name__ == "__main__":
    agent = MobileQAAgent()
    TESTS = [
        ("T1", "Open Obsidian, create a new vault named 'InternVault'", "vault"),
        ("T2", "Create a new note titled 'Meeting Notes' with body 'Daily Standup'", "note"),
        ("T3", "Go to Settings and verify that the 'Appearance' tab icon is the color Red", "appearance"),
        ("T4", "Find and click the 'Print to PDF' button in the main file menu", "print_to_pdf"),
    ]
    for tid, tcase, flow in TESTS:
        res = agent.run_test(tid, tcase, flow)
        print(f"🏁 {tid} Result: {res['result']} — {res.get('reason','')}")