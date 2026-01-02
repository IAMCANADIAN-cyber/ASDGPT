import time
import sys
import os
import json
import threading

# Add project root to path
sys.path.append(os.getcwd())

from core.intervention_engine import InterventionEngine
from core.intervention_library import InterventionLibrary

# Mocks
class MockLogger:
    def log_info(self, msg): print(f"[INFO] {msg}")
    def log_debug(self, msg): print(f"[DEBUG] {msg}")
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} | {details}")
    def log_event(self, event_type, payload):
        print(f"[EVENT] {event_type}: {payload}")

class MockLogicEngine:
    def __init__(self): self.mode = "active"
    def get_mode(self): return self.mode
    def set_mode(self, mode): self.mode = mode

class MockTrayIcon:
    def flash_icon(self, flash_status, original_status):
        print(f"[TRAY] Flash {flash_status} (prev: {original_status})")

class MockApp:
    def __init__(self):
        self.data_logger = MockLogger()
        self.tray_icon = MockTrayIcon()

def test_harness():
    print("Initializing Replay Harness for InterventionEngine...")

    app = MockApp()
    logic = MockLogicEngine()
    engine = InterventionEngine(logic, app)

    # Test cases
    test_cases = [
        {"id": "box_breathing", "description": "Box Breathing (Physiology)"},
        {"id": "doom_scroll_breaker", "description": "Doom Scroll Breaker (Cognitive)"},
        {"id": "sultry_persona_prompt", "description": "Sultry Persona (Creative)"}
    ]

    for case in test_cases:
        print(f"\n--- Testing: {case['description']} ---")
        engine.start_intervention({"id": case['id']})

        # Simulate wait time for intervention to run a bit
        time.sleep(2)

        # Stop it
        engine.stop_intervention()

        # Wait for thread to clear
        time.sleep(0.5)

if __name__ == "__main__":
    test_harness()
