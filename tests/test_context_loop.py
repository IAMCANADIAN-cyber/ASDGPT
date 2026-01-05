import time
import unittest
from unittest.mock import MagicMock
import numpy as np
import config
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface

class TestContextLoop(unittest.TestCase):
    def setUp(self):
        # Mock LMM Interface
        self.mock_lmm = MagicMock(spec=LMMInterface)
        self.mock_lmm.process_data = MagicMock()

        # We need to capture what is sent to process_data
        self.captured_context = None
        def side_effect(video_data=None, audio_data=None, user_context=None):
            self.captured_context = user_context
            # Return a response that simulates detecting phone usage
            return {
                "state_estimation": {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50},
                "visual_context": ["phone_usage"],
                "suggestion": None
            }
        self.mock_lmm.process_data.side_effect = side_effect

        # Initialize Logic Engine
        self.logic_engine = LogicEngine(lmm_interface=self.mock_lmm)

        # Reduce interval for testing
        self.logic_engine.lmm_call_interval = 0
        self.logic_engine.min_lmm_interval = 0

        # Config override (if not already in config, we might need to hardcode in LogicEngine first,
        # but the plan is to move it to config. For now, LogicEngine has it as 3)
        self.logic_engine.doom_scroll_trigger_threshold = 3

    def test_doom_scroll_context_injection(self):
        """
        Verifies that consecutive 'phone_usage' detections lead to a 'system_alert'
        being injected into the next LMM call context.
        """
        # Data for processing
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        audio = np.zeros(1024)

        # 1. First Pass
        self.logic_engine.process_video_data(frame)
        self.logic_engine.process_audio_data(audio)
        self.logic_engine.context_persistence = {} # Reset manually to be sure
        self.logic_engine._trigger_lmm_analysis(reason="test")

        # Wait for thread
        if self.logic_engine.lmm_thread:
            self.logic_engine.lmm_thread.join()

        # Check persistence (should be 1)
        self.assertEqual(self.logic_engine.context_persistence.get("phone_usage"), 1)

        # 2. Second Pass
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()
        self.assertEqual(self.logic_engine.context_persistence.get("phone_usage"), 2)

        # 3. Third Pass (Threshold reached AFTER this analysis processing)
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()
        self.assertEqual(self.logic_engine.context_persistence.get("phone_usage"), 3)

        # 4. Fourth Pass - This is where the Alert should be sent TO the LMM
        # primarily because persistence is >= 3.
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        # Verify captured context
        self.assertIsNotNone(self.captured_context)
        print(f"Captured Context keys: {self.captured_context.keys()}")

        # This assertion is expected to FAIL until implementation is complete
        self.assertIn("system_alerts", self.captured_context, "system_alerts key missing from user_context")
        alerts = self.captured_context["system_alerts"]
        self.assertTrue(any("Doom Scrolling" in a for a in alerts), f"Expected Doom Scrolling alert, got: {alerts}")

if __name__ == '__main__':
    unittest.main()
