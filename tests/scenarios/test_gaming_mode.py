import unittest
from unittest.mock import MagicMock, patch
from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine

class TestGamingMode(unittest.TestCase):
    def setUp(self):
        self.logic_engine = LogicEngine()
        self.intervention_engine = InterventionEngine(self.logic_engine, app_instance=None)

    def test_gaming_mode_suppresses_generic_interventions(self):
        self.logic_engine.set_mode("gaming")

        # Generic distraction alert
        intervention_details = {"id": "distraction_alert"}
        result = self.intervention_engine.start_intervention(intervention_details)

        self.assertFalse(result, "Generic intervention should be suppressed in gaming mode")

    def test_gaming_mode_allows_critical_interventions(self):
        self.logic_engine.set_mode("gaming")

        # Posture check should be allowed
        intervention_details = {"id": "posture_water_reset"}
        # Ensure we don't trigger global cooldown
        self.intervention_engine.last_intervention_time = 0
        result = self.intervention_engine.start_intervention(intervention_details)

        self.assertTrue(result, "Critical intervention 'posture_water_reset' should be allowed in gaming mode")

    def test_gaming_mode_allows_mode_change_notifications(self):
        self.logic_engine.set_mode("gaming")

        intervention_details = {"type": "mode_change_notification", "message": "Test"}
        result = self.intervention_engine.start_intervention(intervention_details, category="mode_change_notification")

        self.assertTrue(result, "Mode change notifications should be allowed in gaming mode")

    def test_high_video_activity_ignored_in_gaming_mode(self):
        self.logic_engine.set_mode("gaming")

        # Mock high video activity conditions
        self.logic_engine.video_activity = self.logic_engine.video_activity_threshold_high + 10
        self.logic_engine.face_metrics = {"face_detected": True, "face_count": 1}
        self.logic_engine.last_lmm_call_time = 0

        with patch.object(self.logic_engine, '_trigger_lmm_analysis') as mock_trigger:
            self.logic_engine.update()

            # Since mode is 'gaming', high_video_activity should NOT trigger LMM analysis
            # It might trigger periodic_check though.

            triggered_reasons = []
            for call in mock_trigger.call_args_list:
                _, kwargs = call
                triggered_reasons.append(kwargs.get('reason'))

            self.assertNotIn("high_video_activity", triggered_reasons, "high_video_activity should not trigger in gaming mode")

if __name__ == "__main__":
    unittest.main()