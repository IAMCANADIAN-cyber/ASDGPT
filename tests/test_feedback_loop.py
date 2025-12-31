import time
import sys
import os

# Ensure we can import core
sys.path.append(os.getcwd())

import config
from core.intervention_engine import InterventionEngine

# Mock config
config.MIN_TIME_BETWEEN_INTERVENTIONS = 0
config.FEEDBACK_SUPPRESSION_MINUTES = 60 # 1 hour for test

class MockApp:
    def __init__(self):
        self.data_logger = self
        self.tray_icon = self
    def log_info(self, msg): print(f"[INFO] {msg}")
    def log_debug(self, msg): print(f"[DEBUG] {msg}")
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")
    def log_event(self, event_type, payload): pass
    def flash_icon(self, flash_status, original_status): pass

class MockLogicEngine:
    def get_mode(self): return "active"

def test_feedback_loop():
    print("--- Testing Feedback Loop ---")
    app = MockApp()
    logic = MockLogicEngine()
    engine = InterventionEngine(logic, app)

    intervention_id = "test_feedback_intervention"
    details = {
        "id": intervention_id,
        "type": intervention_id,
        "message": "Testing feedback",
        "duration": 0.1
    }

    # 1. Start Intervention
    print("\n1. Starting Initial Intervention...")
    success = engine.start_intervention(details)
    if not success:
        print("FAILURE: Initial start failed.")
        return
    time.sleep(0.2) # Let it finish

    # 2. Register Unhelpful Feedback
    print("\n2. Registering 'unhelpful' feedback...")
    engine.register_feedback("unhelpful")

    # Verify suppression list
    if intervention_id in engine.suppressed_interventions:
        print(f"SUCCESS: {intervention_id} added to suppression list.")
    else:
        print("FAILURE: Intervention NOT suppressed.")
        return

    # 3. Try Start Again (Should fail)
    print("\n3. Attempting to start suppressed intervention...")
    success = engine.start_intervention(details)
    if not success:
        print("SUCCESS: Suppressed intervention correctly blocked.")
    else:
        print("FAILURE: Suppressed intervention was allowed to start.")
        return

    # 4. Mock Expiry
    print("\n4. Mocking time expiry...")
    # Manually expire it
    engine.suppressed_interventions[intervention_id] = time.time() - 1

    # 5. Try Start Again (Should succeed)
    print("\n5. Attempting to start expired suppression...")
    success = engine.start_intervention(details)
    if success:
        print("SUCCESS: Expired suppression allowed intervention.")
    else:
        print("FAILURE: Expired suppression still blocked intervention.")
        return

    # 6. Check cleanup
    if intervention_id not in engine.suppressed_interventions:
        print("SUCCESS: Suppression entry cleaned up.")
    else:
        print("FAILURE: Suppression entry remains.")

if __name__ == "__main__":
    test_feedback_loop()
