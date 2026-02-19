import time
import numpy as np
import pytest
import config
from core.logic_engine import LogicEngine
from core.data_logger import DataLogger

# Mock classes
class MockLMMInterface:
    def __init__(self):
        self.call_count = 0

    def process_data(self, video_data=None, audio_data=None, user_context=None):
        print("MockLMM: Starting processing (sleeping 1s)...")
        time.sleep(1.0) # Simulate slow network call
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

    def start_intervention(self, suggestion, **kwargs):
        print(f"MockInterventionEngine: Starting {suggestion}")
        self.started_interventions.append(suggestion)

class TestAsyncLogic:
    def test_logic_engine_async_update(self, tmp_path):
        # Setup Logger
        log_file = tmp_path / "test_async_log.txt"
        config.LOG_FILE = str(log_file)
        config.LOG_LEVEL = "DEBUG"
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
        engine.update()
        end_time = time.time()

        duration = end_time - start_time
        print(f"engine.update() returned at {end_time:.4f}")
        print(f"Duration: {duration:.4f} seconds")

        # Assertion: Update should return immediately (non-blocking)
        assert duration < 0.5, "engine.update() blocked the main thread for too long!"

        # Wait to see if background thread finishes (if async)
        print("Waiting 1.5s to see if LMM completes...")
        time.sleep(1.5)

        # Assertion: LMM should have been called
        assert mock_lmm.call_count == 1, f"LMM was called {mock_lmm.call_count} times."

        # Assertion: Intervention should have been triggered
        assert len(mock_intervention.started_interventions) > 0, "No intervention triggered."
