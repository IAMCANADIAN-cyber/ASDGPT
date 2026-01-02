import time
import threading
import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.logic_engine import LogicEngine
from core.data_logger import DataLogger
import config

# Mock classes
class MockLMMInterface:
    def __init__(self):
        self.call_count = 0

    def process_data(self, video_data=None, audio_data=None, user_context=None):
        print("MockLMM: Starting processing (sleeping 2s)...")
        time.sleep(2.0) # Simulate slow network call
        print("MockLMM: Finished processing.")
        self.call_count += 1
        return {
            "state_estimation": {"arousal": 50, "overload": 10, "focus": 60, "energy": 75, "mood": 55},
            "suggestion": {"id": "test_intervention", "message": "Test"}
        }

    def get_intervention_suggestion(self, analysis):
        return analysis.get("suggestion")

class MockInterventionEngine:
    def __init__(self):
        self.started_interventions = []

    def start_intervention(self, suggestion):
        print(f"MockInterventionEngine: Starting {suggestion}")
        self.started_interventions.append(suggestion)

def run_test():
    # Setup Logger
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "test_async_log.txt"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"
    logger = DataLogger(log_file_path=config.LOG_FILE)

    mock_lmm = MockLMMInterface()
    mock_intervention = MockInterventionEngine()

    engine = LogicEngine(logger=logger, lmm_interface=mock_lmm)
    engine.set_intervention_engine(mock_intervention)

    # Configure engine to trigger immediately
    engine.lmm_call_interval = 0.5
    engine.min_lmm_interval = 0
    engine.last_lmm_call_time = 0

    # Feed dummy data so prepare_lmm_data succeeds
    engine.process_video_data(np.zeros((100, 100, 3), dtype=np.uint8))
    engine.process_audio_data(np.zeros(1024))

    print("\n--- Test: LogicEngine Update Latency ---")

    # Force a trigger condition (periodic check will do if last call time is 0)

    start_time = time.time()
    print(f"Calling engine.update() at {start_time:.4f}")
    engine.update()
    end_time = time.time()

    duration = end_time - start_time
    print(f"engine.update() returned at {end_time:.4f}")
    print(f"Duration: {duration:.4f} seconds")

    if duration > 1.0:
        print("FAIL: engine.update() blocked the main thread for too long!")
    else:
        print("PASS: engine.update() returned immediately.")

    # Wait to see if background thread finishes (if async)
    print("Waiting 3s to see if LMM completes...")
    time.sleep(3.0)

    if mock_lmm.call_count == 1:
        print("PASS: LMM was called.")
    else:
        print(f"FAIL: LMM was called {mock_lmm.call_count} times.")

    if len(mock_intervention.started_interventions) > 0:
        print("PASS: Intervention triggered.")
    else:
        print("FAIL: No intervention triggered.")

if __name__ == "__main__":
    run_test()
