import time
import threading
import sys
import os

# Ensure we can import core
sys.path.append(os.getcwd())

import config
from core.intervention_engine import InterventionEngine
from core.intervention_library import InterventionLibrary

# Mock config to avoid cooldown issues
config.MIN_TIME_BETWEEN_INTERVENTIONS = 0
config.DEFAULT_INTERVENTION_DURATION = 10

class MockApp:
    def __init__(self):
        self.data_logger = self
        self.tray_icon = self
    def log_info(self, msg): print(f"[INFO] {msg}")
    def log_debug(self, msg): print(f"[DEBUG] {msg}")
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")
    def log_event(self, t, p): pass
    def flash_icon(self, flash_status, original_status): pass

class MockLogicEngine:
    def get_mode(self): return "active"

def test_sequence_execution():
    print("--- Testing Sequence Execution ---")
    app = MockApp()
    logic = MockLogicEngine()
    engine = InterventionEngine(logic, app)

    # Define a test sequence manually to verify engine capability
    test_sequence = [
        {"action": "speak", "text": "Step 1"},
        {"action": "wait", "duration": 0.5},
        {"action": "speak", "text": "Step 2"},
    ]

    details = {
        "type": "sequence_test",
        "sequence": test_sequence,
        "duration": 5
    }

    start = time.time()
    engine.start_intervention(details)

    # Wait for thread to finish
    if engine.intervention_thread:
        engine.intervention_thread.join()

    end = time.time()
    duration = end - start
    print(f"Sequence took {duration:.2f} seconds")

    # Expect roughly 0.5s wait + execution time. Should be > 0.5 and < 1.0 ideally
    if duration >= 0.5:
        print("SUCCESS: Duration matches expected sequence wait.")
    else:
        print("FAILURE: Sequence too fast.")

def test_library_lookup():
    print("\n--- Testing Library Lookup ---")
    app = MockApp()
    logic = MockLogicEngine()
    engine = InterventionEngine(logic, app)

    # Use an actual library ID
    box_id = "phys_box_breathing"

    # We won't run the full thing (it's long), just start it and stop it
    # But first, let's verify lookup works by inspecting the thread start

    # Monkey patch _run_intervention_thread just to inspect `_current_intervention_details`
    original_run = engine._run_intervention_thread

    captured_details = {}
    def spy_run():
        nonlocal captured_details
        captured_details = engine._current_intervention_details.copy()
        # Don't actually run the long sequence
        engine._intervention_active.clear()

    engine._run_intervention_thread = spy_run

    success = engine.start_intervention({"id": box_id})
    if not success:
        print("FAILURE: Could not start intervention by ID.")
        return

    print(f"Captured Details Type: {captured_details.get('type')}")
    print(f"Captured Details Sequence Len: {len(captured_details.get('sequence', []))}")

    if captured_details.get("type") == "phys_box_breathing" and len(captured_details.get("sequence", [])) > 5:
        print("SUCCESS: Library lookup correctly populated details.")
    else:
        print("FAILURE: Library lookup failed or incomplete.")

if __name__ == "__main__":
    test_sequence_execution()
    test_library_lookup()
