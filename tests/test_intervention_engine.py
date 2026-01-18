import unittest
from unittest.mock import MagicMock, patch, ANY
import time
import json
import os
import sys
import tempfile
import shutil

# We do not patch sys.modules globally anymore to avoid pollution.
# Instead, we will rely on unittest.mock.patch where needed,
# or assume the environment has the dependencies (which it does now).

from core.intervention_engine import InterventionEngine
import config

class TestInterventionEngine(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for config files
        self.test_dir = tempfile.mkdtemp()
        self.prefs_file = os.path.join(self.test_dir, "prefs.json")
        self.suppressions_file = os.path.join(self.test_dir, "suppressions.json")

        # Patch config values
        self.config_patcher = patch.multiple(config,
            PREFERENCES_FILE=self.prefs_file,
            SUPPRESSIONS_FILE=self.suppressions_file,
            MIN_TIME_BETWEEN_INTERVENTIONS=10
        )
        self.config_patcher.start()

        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()

        # Patch dependencies that might be missing or need mocking
        # We patch at the module level where they are used
        self.sd_patcher = patch('core.intervention_engine.sd', MagicMock())
        self.sd_patcher.start()

        self.wav_patcher = patch('core.intervention_engine.wavfile', MagicMock())
        self.wav_patcher.start()

        self.pil_patcher = patch('core.intervention_engine.Image', MagicMock())
        self.pil_patcher.start()

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)

        # Reset internal state
        self.engine.suppressed_interventions = {}
        self.engine.preferred_interventions = {}
        self.engine.last_intervention_time = 0

    def tearDown(self):
        self.config_patcher.stop()
        self.sd_patcher.stop()
        self.wav_patcher.stop()
        self.pil_patcher.stop()
        shutil.rmtree(self.test_dir)

    @patch('threading.Thread')
    def test_start_intervention_library(self, mock_thread_class):
        """Test starting an intervention defined in the library."""
        # We need to make sure the library has the item we are requesting
        # The real InterventionLibrary is used, so we check for a real ID like "box_breathing"
        result = self.engine.start_intervention({"id": "box_breathing"})
        self.assertTrue(result)
        self.assertTrue(self.engine._intervention_active.is_set())
        mock_thread_class.assert_called_once()

    @patch('threading.Thread')
    def test_start_intervention_adhoc(self, mock_thread_class):
        """Test starting a custom ad-hoc intervention."""
        result = self.engine.start_intervention({"type": "test_type", "message": "Test message"})
        self.assertTrue(result)
        self.assertEqual(self.engine._current_intervention_details["type"], "test_type")
        mock_thread_class.assert_called_once()

    def test_start_intervention_missing_data(self):
        """Test that start_intervention fails without id or type+message."""
        result = self.engine.start_intervention({"some": "garbage"})
        self.assertFalse(result)

    def test_start_intervention_mode_suppression(self):
        """Test that intervention is suppressed if mode is not active."""
        self.mock_logic.get_mode.return_value = "paused"
        result = self.engine.start_intervention({"id": "box_breathing"})
        self.assertFalse(result)

    def test_start_intervention_manual_suppression(self):
        """Test that intervention is skipped if manually suppressed."""
        # box_breathing id corresponds to "box_breathing" type in logic (id=type)
        self.engine.suppress_intervention("box_breathing", 60)

        # Verify it was added
        self.assertIn("box_breathing", self.engine.suppressed_interventions)

        result = self.engine.start_intervention({"id": "box_breathing"})
        self.assertFalse(result)

    def test_start_intervention_rate_limit(self):
        """Test minimum time between interventions."""
        # Config is patched to 10s in setUp

        # Start one
        with patch('threading.Thread'):
            self.engine.start_intervention({"type": "t1", "message": "m1"})

        # Immediate next one should fail
        result = self.engine.start_intervention({"type": "t2", "message": "m2"})
        self.assertFalse(result)

        # Wait (simulate time passing by manipulating last_intervention_time)
        self.engine.last_intervention_time = time.time() - 20
        with patch('threading.Thread'):
            result = self.engine.start_intervention({"type": "t2", "message": "m2"})
        self.assertTrue(result)

    def test_stop_intervention(self):
        self.engine._intervention_active.set()
        self.engine.stop_intervention()
        self.assertFalse(self.engine._intervention_active.is_set())

    def test_register_feedback_valid(self):
        """Test registering feedback for a valid intervention."""
        self.engine.last_feedback_eligible_intervention = {
            "message": "Test msg",
            "type": "test_type",
            "timestamp": time.time()
        }
        self.engine.feedback_window = 60

        self.engine.register_feedback("Helpful")

        self.mock_app.data_logger.log_event.assert_called_with(
            event_type="user_feedback",
            payload=ANY
        )
        self.assertIn("test_type", self.engine.preferred_interventions)
        self.assertEqual(self.engine.preferred_interventions["test_type"]["count"], 1)

    def test_register_feedback_expired(self):
        """Test feedback ignored if window expired."""
        self.engine.last_feedback_eligible_intervention = {
            "message": "Test msg",
            "type": "test_type",
            "timestamp": time.time() - 100
        }
        self.engine.feedback_window = 10

        self.engine.register_feedback("Helpful")

        self.mock_app.data_logger.log_event.assert_not_called()

    def test_feedback_suppression_unhelpful(self):
        """Test that 'Unhelpful' feedback triggers suppression."""
        self.engine.last_feedback_eligible_intervention = {
            "message": "Test msg",
            "type": "test_type",
            "timestamp": time.time()
        }

        self.engine.register_feedback("Unhelpful")

        self.assertIn("test_type", self.engine.suppressed_interventions)

    def test_run_sequence_execution(self):
        """Test that _run_sequence calls appropriate methods."""
        sequence = [
            {"action": "speak", "content": "Hello"},
            {"action": "wait", "duration": 0.1},
            {"action": "visual_prompt", "content": "image.png"}
        ]

        self.engine._speak = MagicMock()
        self.engine._wait = MagicMock()
        self.engine._show_visual_prompt = MagicMock()

        self.engine._intervention_active.set()
        self.engine._run_sequence(sequence, self.mock_app.data_logger)

        self.engine._speak.assert_called_with("Hello", blocking=True)
        self.engine._wait.assert_called_with(0.1)
        self.engine._show_visual_prompt.assert_called_with("image.png")

    def test_get_suppressed_intervention_types(self):
        self.engine.suppress_intervention("type_a", 10)
        # Manually inject expired one
        self.engine.suppressed_interventions["type_b"] = time.time() - 100

        suppressed = self.engine.get_suppressed_intervention_types()
        self.assertIn("type_a", suppressed)
        self.assertNotIn("type_b", suppressed)

if __name__ == '__main__':
    unittest.main()
