import unittest
import time
import os
import json
from unittest.mock import MagicMock, patch
import config

# Import InterventionEngine (dependencies will be mocked via patch in setUp)
from core.intervention_engine import InterventionEngine

class TestFeedbackLoop(unittest.TestCase):
    def setUp(self):
        # Patch sys.modules to mock dependencies before they are used
        self.patcher_sd = patch.dict('sys.modules', {'sounddevice': MagicMock()})
        self.patcher_scipy = patch.dict('sys.modules', {'scipy.io.wavfile': MagicMock()})
        self.patcher_pil = patch.dict('sys.modules', {'PIL': MagicMock()})

        self.patcher_sd.start()
        self.patcher_scipy.start()
        self.patcher_pil.start()

        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"

        self.mock_app = MagicMock()
        self.mock_app.data_logger = MagicMock()
        self.mock_app.tray_icon = MagicMock()

        # Update config to use a test path for suppressions
        self.test_suppressions_file = os.path.join(os.getcwd(), "test_suppressions.json")
        self.original_suppressions_file = getattr(config, 'SUPPRESSIONS_FILE', 'user_data/suppressions.json')
        config.SUPPRESSIONS_FILE = self.test_suppressions_file

        # Override config.MIN_TIME_BETWEEN_INTERVENTIONS
        self.original_min_time = config.MIN_TIME_BETWEEN_INTERVENTIONS
        config.MIN_TIME_BETWEEN_INTERVENTIONS = 0

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)
        self.engine.feedback_window = 100

    def tearDown(self):
        # Stop patches
        self.patcher_sd.stop()
        self.patcher_scipy.stop()
        self.patcher_pil.stop()

        if os.path.exists(self.test_suppressions_file):
            os.remove(self.test_suppressions_file)
        self.engine.shutdown()

        # Restore config
        config.MIN_TIME_BETWEEN_INTERVENTIONS = self.original_min_time
        config.SUPPRESSIONS_FILE = self.original_suppressions_file

    def test_feedback_storage(self):
        details = {"id": "box_breathing"}
        self.engine.last_intervention_time = 0
        success = self.engine.start_intervention(details)
        self.assertTrue(success)

        time.sleep(0.1)
        self.engine.stop_intervention()
        time.sleep(0.1)

        self.assertIsNotNone(self.engine.last_feedback_eligible_intervention["message"])
        self.assertEqual(self.engine.last_feedback_eligible_intervention["type"], "box_breathing")

    def test_suppression_logic(self):
        # 1. Run intervention
        self.engine.last_intervention_time = 0
        self.engine.start_intervention({"id": "box_breathing"})
        time.sleep(0.1)
        self.engine.stop_intervention()
        time.sleep(0.1)

        # 2. Register Unhelpful Feedback
        self.engine.register_feedback("Unhelpful")

        # 3. Verify it is in suppression list
        self.assertIn("box_breathing", self.engine.suppressed_interventions)

        # 4. Try to run it again.
        self.engine.last_intervention_time = 0
        # Ensure thread is cleared
        if self.engine.intervention_thread:
            self.engine.intervention_thread.join(timeout=1)

        result = self.engine.start_intervention({"id": "box_breathing"})
        self.assertFalse(result, "Intervention should have been suppressed")

        # 5. Different one should run
        self.engine.last_intervention_time = 0
        result2 = self.engine.start_intervention({"id": "visual_scan"})
        self.assertTrue(result2, "Different intervention should run")

    def test_suppression_persistence(self):
        self.engine.suppress_intervention("test_type", 60)

        # Check file
        self.assertTrue(os.path.exists(self.test_suppressions_file), f"File {self.test_suppressions_file} not created")

        with open(self.test_suppressions_file, 'r') as f:
            data = json.load(f)
            self.assertIn("test_type", data)

if __name__ == '__main__':
    unittest.main()
