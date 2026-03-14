import unittest
from unittest.mock import MagicMock, patch
from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine

class TestGamingMode(unittest.TestCase):
    def setUp(self):
        # Setup mock logger
        self.mock_logger = MagicMock()

        # Setup mock LMM interface
        self.mock_lmm = MagicMock()
        self.mock_lmm.process_data.return_value = {
            "state_estimation": {"arousal": 50},
            "suggestion": None
        }

        # Set up logic engine
        self.logic_engine = LogicEngine(lmm_interface=self.mock_lmm, logger=self.mock_logger)

        # Set up intervention engine
        self.intervention_engine = InterventionEngine(self.logic_engine)
        self.logic_engine.set_intervention_engine(self.intervention_engine)

        # Mock start_intervention internally to test suppression correctly
        # Actually, we test if start_intervention returns False when suppressed.

    @patch('core.logic_engine.LogicEngine.get_mode')
    def test_high_video_activity_suppression(self, mock_get_mode):
        mock_get_mode.return_value = "gaming"

        # Test intervention suppression
        # Attempt to start a non-critical intervention
        intervention_details = {"type": "distraction_alert", "message": "You are distracted."}
        result = self.intervention_engine.start_intervention(intervention_details)

        # Should be suppressed
        self.assertFalse(result)

    @patch('core.logic_engine.LogicEngine.get_mode')
    def test_posture_reset_allowed(self, mock_get_mode):
        mock_get_mode.return_value = "gaming"

        # Setup an intervention card in the mock library to avoid errors, or just pass ad-hoc
        intervention_details = {"type": "posture_water_reset", "message": "Check your posture."}

        # Allow it to run but mock the actual execution thread to not hang
        with patch.object(self.intervention_engine, '_run_intervention_thread'):
            result = self.intervention_engine.start_intervention(intervention_details)

            # Should NOT be suppressed
            self.assertTrue(result)

    @patch('core.logic_engine.LogicEngine.get_mode')
    def test_mode_change_notification_allowed(self, mock_get_mode):
        mock_get_mode.return_value = "gaming"

        intervention_details = {"type": "mode_change_notification", "message": "Mode changed."}

        with patch.object(self.intervention_engine, '_run_intervention_thread'):
            result = self.intervention_engine.start_intervention(intervention_details)

            # Should NOT be suppressed
            self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
