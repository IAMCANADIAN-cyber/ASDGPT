import time
import json
import threading
from typing import Dict, Any, List, Optional
from core.intervention_engine import InterventionEngine
from core.intervention_library import InterventionLibrary

# Mock Logic Engine
class MockLogicEngine:
    def __init__(self):
        self.mode = "active"
    def get_mode(self): return self.mode
    def set_mode(self, mode): self.mode = mode

# Mock App / Logger
class MockDataLogger:
    def log_info(self, msg): print(f"[INFO] {msg}")
    def log_debug(self, msg): print(f"[DEBUG] {msg}")
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} | {details}")
    def log_event(self, event_type, payload):
        print(f"[EVENT] {event_type}: {payload}")

class MockApp:
    def __init__(self):
        self.data_logger = MockDataLogger()
        self.tray_icon = None

# Extended InterventionEngine to mock actions
class TestInterventionEngine(InterventionEngine):
    def __init__(self, logic_engine, app_instance):
        super().__init__(logic_engine, app_instance)
        self.actions_executed = []
        self.mock_wait_duration = 0.01

    def _speak(self, text: str) -> None:
        self.actions_executed.append(f"SPEAK: {text}")
        super()._speak(text)

    def _play_sound(self, file_path: str) -> None:
        self.actions_executed.append(f"SOUND: {file_path}")
        super()._play_sound(file_path)

    def _show_visual_prompt(self, content: str) -> None:
        self.actions_executed.append(f"VISUAL: {content}")
        super()._show_visual_prompt(content)

    def _wait(self, duration: float) -> None:
        self.actions_executed.append(f"WAIT: {duration}s")
        # In test, we can simulate waiting by checking stop flag in a loop
        # but for short tests we just sleep a tiny bit.
        # If we want to test interruption, we need to sleep long enough to catch it.
        start = time.time()
        # Sleep for self.mock_wait_duration (default fast)
        # But loop to respect stop flag
        while time.time() - start < self.mock_wait_duration:
            if not self._intervention_active.is_set():
                break
            time.sleep(0.01)

    def _capture_image(self, details: str) -> None:
        self.actions_executed.append(f"CAPTURE: {details}")
        super()._capture_image(details)

    def _record_video(self, details: str) -> None:
        self.actions_executed.append(f"RECORD: {details}")
        super()._record_video(details)

def run_test():
    print("=== Intervention Replay Harness ===")

    mock_logic = MockLogicEngine()
    mock_app = MockApp()

    # Initialize Engine
    engine = TestInterventionEngine(mock_logic, mock_app)

    # Get Library
    library = InterventionLibrary()

    # 1. Test "Box Breathing" (Sequence)
    print("\n--- Test 1: Box Breathing (Sequence) ---")
    card_id = "box_breathing"
    engine.actions_executed = []

    success = engine.start_intervention({"id": card_id})
    if not success:
        print("Failed to start intervention")
        return

    # Wait for thread to finish
    while engine._intervention_active.is_set():
        time.sleep(0.1)

    print("Actions Executed:")
    for action in engine.actions_executed:
        print(f"  - {action}")

    assert len(engine.actions_executed) > 0
    assert "SPEAK: Let's reset. Breathe in for 4." in engine.actions_executed
    assert "WAIT: 4s" in engine.actions_executed

    # 2. Test "Sultry Persona Prompt" (Capture Image)
    print("\n--- Test 2: Sultry Persona Prompt (Capture Image) ---")
    card_id = "sultry_persona_prompt"
    engine.actions_executed = []

    # Reset last intervention time to allow immediate run
    engine.last_intervention_time = 0

    success = engine.start_intervention({"id": card_id})

    while engine._intervention_active.is_set():
        time.sleep(0.1)

    print("Actions Executed:")
    for action in engine.actions_executed:
        print(f"  - {action}")

    assert any("CAPTURE: Capturing sultry image..." in s for s in engine.actions_executed)

    # 3. Test Interruption
    print("\n--- Test 3: Interruption ---")
    card_id = "visual_scan" # Has speak -> wait(15) -> speak
    engine.actions_executed = []
    engine.last_intervention_time = 0
    engine.mock_wait_duration = 0.5 # Make wait long enough to interrupt

    engine.start_intervention({"id": card_id})
    time.sleep(0.1) # Let it start and execute first speak and enter wait
    engine.stop_intervention() # Interrupt
    time.sleep(0.1) # Let thread exit

    print("Actions Executed:")
    for action in engine.actions_executed:
        print(f"  - {action}")

    # Should perform first speak, enter wait, but NOT perform second speak
    assert "SPEAK: Quick game. Find 5 blue objects in the room. Go." in engine.actions_executed
    assert "WAIT: 15s" in engine.actions_executed
    assert "SPEAK: Done." not in engine.actions_executed

    print("\n=== All Tests Passed ===")

if __name__ == "__main__":
    run_test()
