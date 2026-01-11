import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import os

# Add project root to sys.path to ensure modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies that might require hardware or complex setup
# We use patch.dict or module-level mocks CAREFULLY.
# numpy is NOT mocked because LogicEngine uses it for real calculations.
sys.modules['cv2'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

# Import the module under test
# We need to make sure config and other core modules are importable
import core.logic_engine as logic_engine
import config

class TestDNDMode(unittest.TestCase):
    def setUp(self):
        # Setup LogicEngine with mocks
        self.mock_logger = MagicMock()
        self.mock_lmm = MagicMock()
        self.mock_intervention = MagicMock()

        self.engine = logic_engine.LogicEngine(
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )
        self.engine.set_intervention_engine(self.mock_intervention)

        # Ensure we start in active mode
        self.engine.current_mode = "active"

    def test_dnd_mode_transition(self):
        """Test transitioning to and from DND mode."""
        self.engine.set_mode("dnd")
        self.assertEqual(self.engine.get_mode(), "dnd")

        self.engine.set_mode("active")
        self.assertEqual(self.engine.get_mode(), "active")

    def test_dnd_suppresses_lmm_interventions(self):
        """Test that DND mode suppresses interventions suggested by LMM."""
        self.engine.set_mode("dnd")

        # Configure LMM to suggest an intervention
        self.mock_lmm.process_data.return_value = {
            "suggestion": {"id": "box_breathing"},
            "state_estimation": {"arousal": 50},
            "visual_context": []
        }
        self.mock_lmm.get_intervention_suggestion.return_value = {"id": "box_breathing"}

        # Direct test of _run_lmm_analysis_async with allow_intervention=False
        payload = {
            "video_data": None,
            "audio_data": None,
            "user_context": {"trigger_reason": "periodic"}
        }
        self.engine._run_lmm_analysis_async(payload, allow_intervention=False)

        # Verify intervention engine was NOT called
        self.mock_intervention.start_intervention.assert_not_called()
        # Verify we logged the suppression
        self.mock_logger.log_info.assert_any_call("Intervention suggested but suppressed due to mode: {'id': 'box_breathing'}")

    def test_dnd_suppresses_reflexive_interventions(self):
        """Test that DND mode suppresses system/reflexive triggers like doom scrolling."""
        self.engine.set_mode("dnd")

        # Configure LMM to return visual context that triggers doom scrolling
        self.mock_lmm.process_data.return_value = {
            "suggestion": None,
            "state_estimation": {"arousal": 50},
            "visual_context": ["phone_usage"]
        }

        # Set threshold low so it triggers immediately
        self.engine.doom_scroll_trigger_threshold = 1

        # Run analysis with allow_intervention=False
        payload = {
            "video_data": None,
            "audio_data": None,
            "user_context": {"trigger_reason": "periodic"}
        }
        self.engine._run_lmm_analysis_async(payload, allow_intervention=False)

        # Verify logic detected the trigger
        self.mock_intervention.start_intervention.assert_not_called()
        self.mock_logger.log_info.assert_any_call("Intervention suggested but suppressed due to mode: {'id': 'doom_scroll_breaker'}")

    def test_dnd_monitoring_continues(self):
        """Test that DND mode still performs LMM analysis (monitoring) but just suppresses output."""
        self.engine.set_mode("dnd")

        with patch.object(self.engine, '_trigger_lmm_analysis') as mock_trigger:
            self.engine.last_lmm_call_time = 0
            self.engine.lmm_call_interval = 0 # Force immediate
            self.engine.update()

            mock_trigger.assert_called_with(allow_intervention=False)

if __name__ == '__main__':
    unittest.main()
