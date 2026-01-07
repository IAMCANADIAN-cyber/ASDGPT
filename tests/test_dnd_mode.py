import unittest
import time
import sys
import os
import threading
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.logic_engine import LogicEngine
from core.data_logger import DataLogger
import config

class MockLMMInterface:
    def __init__(self):
        self.last_call_data = None
        self.call_count = 0

    def process_data(self, video_data=None, audio_data=None, user_context=None):
        self.last_call_data = {
            "user_context": user_context
        }
        self.call_count += 1
        return {
            "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
            "visual_context": [],
            "suggestion": {"type": "test_intervention", "message": "Test"}
        }

    def get_intervention_suggestion(self, analysis):
        return analysis.get("suggestion")

class MockInterventionEngine:
    def __init__(self):
        self.interventions_triggered = []

    def start_intervention(self, suggestion):
        self.interventions_triggered.append(suggestion)

class TestDNDMode(unittest.TestCase):
    def setUp(self):
        self.logger = DataLogger(log_file_path="test_dnd.log")
        self.mock_lmm = MockLMMInterface()
        self.mock_intervention = MockInterventionEngine()
        self.logic_engine = LogicEngine(logger=self.logger, lmm_interface=self.mock_lmm)
        self.logic_engine.set_intervention_engine(self.mock_intervention)

        # Adjust settings for faster test
        self.logic_engine.lmm_call_interval = 1
        self.logic_engine.min_lmm_interval = 0
        self.logic_engine.audio_threshold_high = 0.5

    def tearDown(self):
        self.logic_engine.shutdown()

    def test_dnd_suppresses_intervention(self):
        """
        Test that DND mode allows monitoring (LMM calls) but suppresses interventions.
        """
        # 1. Set DND mode
        self.logic_engine.set_mode("dnd")
        self.assertEqual(self.logic_engine.get_mode(), "dnd")

        # 2. Trigger high audio (which normally triggers intervention)
        loud_audio = np.ones(1024) * 0.8
        self.logic_engine.process_audio_data(loud_audio)
        self.logic_engine.process_video_data(np.zeros((100, 100, 3), dtype=np.uint8)) # Need video data too

        # Force eligibility
        self.logic_engine.last_lmm_call_time = time.time() - 10

        # Update
        self.logic_engine.update()

        # Wait for async thread
        if self.logic_engine.lmm_thread:
            self.logic_engine.lmm_thread.join(timeout=2)

        # 3. Verify LMM was called (Monitoring is active)
        self.assertIsNotNone(self.mock_lmm.last_call_data, "LMM should be called in DND mode")
        self.assertEqual(self.mock_lmm.last_call_data['user_context']['current_mode'], "dnd")

        # 4. Verify NO intervention was triggered
        self.assertEqual(len(self.mock_intervention.interventions_triggered), 0, "Intervention should be suppressed in DND mode")

    def test_dnd_toggle_logic(self):
        """
        Test toggling in and out of DND mode.
        """
        self.logic_engine.set_mode("active")
        self.assertEqual(self.logic_engine.get_mode(), "active")

        self.logic_engine.set_mode("dnd")
        self.assertEqual(self.logic_engine.get_mode(), "dnd")

        self.logic_engine.set_mode("active")
        self.assertEqual(self.logic_engine.get_mode(), "active")

if __name__ == '__main__':
    unittest.main()
