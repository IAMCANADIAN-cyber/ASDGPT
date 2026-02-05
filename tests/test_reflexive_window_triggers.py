import unittest
from unittest.mock import MagicMock, patch
import time
import sys
from core.logic_engine import LogicEngine

class TestReflexiveWindowTriggers(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_window_sensor = MagicMock()
        self.mock_intervention_engine = MagicMock()
        self.mock_lmm = MagicMock()

        # Patch config for predictable triggers
        self.config_patcher = patch('core.logic_engine.config')
        self.mock_config = self.config_patcher.start()

        # Setup config values
        self.mock_config.REFLEXIVE_WINDOW_TRIGGERS = {
            "Game": "distraction_alert",
            "Social": "distraction_alert"
        }
        self.mock_config.REFLEXIVE_WINDOW_COOLDOWN = 10 # Short cooldown for testing
        self.mock_config.HISTORY_WINDOW_SIZE = 5
        self.mock_config.HISTORY_SAMPLE_INTERVAL = 10
        self.mock_config.AUDIO_THRESHOLD_HIGH = 0.5
        self.mock_config.VIDEO_ACTIVITY_THRESHOLD_HIGH = 20.0
        self.mock_config.DEFAULT_MODE = "active"

        # Create LogicEngine
        self.logic = LogicEngine(
            window_sensor=self.mock_window_sensor,
            lmm_interface=self.mock_lmm
        )
        self.logic.set_intervention_engine(self.mock_intervention_engine)

        # Reload triggers in logic engine because it loads them in __init__
        # But we patched config before init, so it should be fine?
        # Wait, LogicEngine imports config at module level.
        # But we patched 'core.logic_engine.config'.
        # Let's manually inject just to be safe if the patch was too late for module-level load if any.
        self.logic.reflexive_window_triggers = {
            "Game": "distraction_alert",
            "Social": "distraction_alert"
        }
        self.logic.reflexive_window_cooldown = 10
        self.logic.window_check_interval = 0 # Disable throttle for direct testing

    def tearDown(self):
        self.config_patcher.stop()

    def test_check_window_reflexes_match(self):
        """Test basic matching logic."""
        # Match
        self.assertEqual(self.logic._check_window_reflexes("Playing Game"), "distraction_alert")

        # Reset cooldown for next assertion (since both map to same ID)
        self.logic.last_reflexive_trigger_time["distraction_alert"] = 0

        # Case insensitive match
        self.assertEqual(self.logic._check_window_reflexes("social media"), "distraction_alert")

        # No match
        self.assertIsNone(self.logic._check_window_reflexes("Work Document"))

    def test_cooldown_enforcement(self):
        """Test that triggers respect the cooldown."""
        # First trigger
        self.assertEqual(self.logic._check_window_reflexes("Game"), "distraction_alert")

        # Second trigger immediate - should be blocked
        self.assertIsNone(self.logic._check_window_reflexes("Game"))

        # Wait for cooldown
        # We can't easily wait 10s in test, so we manipulate time or the last_time dict
        # Modifying internal state for test speed
        self.logic.last_reflexive_trigger_time["distraction_alert"] = time.time() - 11

        # Should trigger again
        self.assertEqual(self.logic._check_window_reflexes("Game"), "distraction_alert")

    def test_update_integration(self):
        """Test that update() cycle calls intervention engine."""
        self.mock_window_sensor.get_active_window.return_value = "Playing Game"

        # Ensure throttle allows check
        self.logic.last_window_check_time = 0
        self.logic.window_check_interval = 0

        self.logic.update()

        # Check intervention started
        self.mock_intervention_engine.start_intervention.assert_called()

        # Check payload
        args, _ = self.mock_intervention_engine.start_intervention.call_args
        payload = args[0]
        # Depending on config mock state, it might be ID or Type/Message
        # We constructed it such that it tries to use config if available.
        # MagicMock behavior makes config lookup return a Mock, so it enters the "config_def" branch.
        self.assertEqual(payload.get('type') or payload.get('id'), "distraction_alert")

    def test_unknown_window_ignored(self):
        """Unknown window should not trigger."""
        self.mock_window_sensor.get_active_window.return_value = "Unknown"
        self.logic.update()
        self.mock_intervention_engine.start_intervention.assert_not_called()

    def test_throttle(self):
        """Test that window checking is throttled in update."""
        self.logic.window_check_interval = 100
        self.logic.last_window_check_time = time.time() # Just checked

        self.mock_window_sensor.get_active_window.return_value = "Game"

        self.logic.update()
        # Should NOT be called because of throttle
        self.mock_intervention_engine.start_intervention.assert_not_called()

if __name__ == '__main__':
    unittest.main()
