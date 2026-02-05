import unittest
from unittest.mock import MagicMock, patch
import time
import config
from core.logic_engine import LogicEngine

class TestReflexiveWindowTriggers(unittest.TestCase):
    def setUp(self):
        self.logic_engine = LogicEngine()
        self.logic_engine.window_sensor = MagicMock()
        self.logic_engine.intervention_engine = MagicMock()
        self.logic_engine.logger = MagicMock()

        # Reset triggers for test isolation
        self.logic_engine.last_reflexive_trigger_time = 0
        self.logic_engine.last_window_check_time = 0
        self.logic_engine.window_check_interval = 0 # Force check every update

    def test_trigger_on_match(self):
        """Verify intervention triggered on matching window title."""
        self.logic_engine.window_sensor.get_active_window.return_value = "Steam - Library"

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Steam": "distraction_alert"}), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 60):
            self.logic_engine.update()

        self.logic_engine.intervention_engine.start_intervention.assert_called_with({"id": "distraction_alert"})
        self.assertAlmostEqual(self.logic_engine.last_reflexive_trigger_time, time.time(), delta=1)

    def test_no_trigger_on_mismatch(self):
        """Verify no intervention on non-matching window."""
        self.logic_engine.window_sensor.get_active_window.return_value = "Visual Studio Code"

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Steam": "distraction_alert"}), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 60):
            self.logic_engine.update()

        self.logic_engine.intervention_engine.start_intervention.assert_not_called()

    def test_trigger_cooldown(self):
        """Verify triggers respect cooldown."""
        self.logic_engine.window_sensor.get_active_window.return_value = "Steam"

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Steam": "distraction_alert"}), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 60):

            # First trigger
            self.logic_engine.update()
            self.logic_engine.intervention_engine.start_intervention.assert_called_once()
            self.logic_engine.intervention_engine.start_intervention.reset_mock()

            # Immediate second trigger (should be ignored)
            self.logic_engine.update()
            self.logic_engine.intervention_engine.start_intervention.assert_not_called()

            # Reset timestamp to past cooldown
            self.logic_engine.last_reflexive_trigger_time = time.time() - 61

            # Third trigger (should work)
            self.logic_engine.update()
            self.logic_engine.intervention_engine.start_intervention.assert_called_once()

    def test_case_insensitivity(self):
        """Verify trigger is case insensitive."""
        self.logic_engine.window_sensor.get_active_window.return_value = "reddit - chrome"

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Reddit": "distraction_alert"}), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 60):
            self.logic_engine.update()

        self.logic_engine.intervention_engine.start_intervention.assert_called_with({"id": "distraction_alert"})

    def test_unknown_window_ignored(self):
        """Verify 'Unknown' window does not trigger even if mapped (though unlikely)."""
        self.logic_engine.window_sensor.get_active_window.return_value = "Unknown"

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Unknown": "alert"}), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 60):
            self.logic_engine.update()

        self.logic_engine.intervention_engine.start_intervention.assert_not_called()

    def test_window_sensor_failure_handled(self):
        """Verify LogicEngine handles WindowSensor exceptions gracefully."""
        self.logic_engine.window_sensor.get_active_window.side_effect = Exception("Sensor Error")

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Steam": "alert"}):
            try:
                self.logic_engine.update()
            except Exception as e:
                self.fail(f"LogicEngine.update raised exception on sensor failure: {e}")

            self.logic_engine.intervention_engine.start_intervention.assert_not_called()

if __name__ == '__main__':
    unittest.main()
