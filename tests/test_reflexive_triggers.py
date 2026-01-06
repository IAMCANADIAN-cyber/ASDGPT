import time
import unittest
from unittest.mock import MagicMock
import numpy as np
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface
from core.intervention_engine import InterventionEngine

class TestReflexiveTriggers(unittest.TestCase):
    def setUp(self):
        # Mock LMM Interface
        self.mock_lmm = MagicMock(spec=LMMInterface)
        self.mock_lmm.process_data = MagicMock()
        self.mock_lmm.get_intervention_suggestion = MagicMock(return_value=None)

        # Mock Intervention Engine
        self.mock_intervention_engine = MagicMock(spec=InterventionEngine)
        self.mock_intervention_engine.start_intervention = MagicMock()

        # Initialize Logic Engine
        self.logic_engine = LogicEngine(lmm_interface=self.mock_lmm)
        self.logic_engine.set_intervention_engine(self.mock_intervention_engine)

        # Config override
        self.logic_engine.doom_scroll_trigger_threshold = 3
        self.logic_engine.lmm_call_interval = 0
        self.logic_engine.min_lmm_interval = 0

    def test_doom_scroll_trigger_execution(self):
        """
        Verifies that when 'doom_scroll' threshold is reached,
        the LogicEngine PROACTIVELY calls start_intervention
        with 'doom_scroll_breaker', even if LMM suggests nothing.
        """
        # Setup LMM to return "phone_usage" tag
        self.mock_lmm.process_data.return_value = {
            "state_estimation": {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50},
            "visual_context": ["phone_usage"],
            "suggestion": None
        }

        # Data
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        audio = np.zeros(1024)
        self.logic_engine.process_video_data(frame)
        self.logic_engine.process_audio_data(audio)

        # Pass 1
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        # Pass 2
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        # Pass 3 (Threshold Hit)
        # The trigger happens inside the thread processing the response
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        # Verification
        # At this point, the logic engine should have detected the persistence threshold
        # and immediately triggered the intervention.

        # Check if start_intervention was called with correct ID
        self.mock_intervention_engine.start_intervention.assert_called()

        # Inspect the call args
        args, _ = self.mock_intervention_engine.start_intervention.call_args
        intervention_details = args[0]

        print(f"Intervention Triggered: {intervention_details}")

        self.assertEqual(intervention_details.get("id"), "doom_scroll_breaker")

if __name__ == '__main__':
    unittest.main()
