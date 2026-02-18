import unittest
from unittest.mock import MagicMock, patch
import time
from core.intervention_engine import InterventionEngine
import config

class TestInterventionEscalation(unittest.TestCase):
    def setUp(self):
        self.mock_logic_engine = MagicMock()
        self.mock_logic_engine.get_mode.return_value = "active" # Allow interventions
        self.mock_app = MagicMock()
        self.mock_app.data_logger = MagicMock()

        # Ensure we have clean state
        with patch("core.intervention_engine.InterventionLibrary") as MockLib:
             self.engine = InterventionEngine(self.mock_logic_engine, self.mock_app)
             # Mock the library response so get_intervention_by_id returns a valid dummy card
             self.engine.library.get_intervention_by_id.return_value = {
                 "id": "test_id",
                 "tier": 1,
                 "sequence": []
             }

        # Shorten windows for testing
        self.engine.escalation_window = 1.0 # 1 second

        # Mock the thread runner so we don't spawn threads
        self.engine._run_intervention_thread = MagicMock()

    def test_escalation_logic(self):
        # Patch the config constant used in the module
        with patch("core.intervention_engine.config.MIN_TIME_BETWEEN_INTERVENTIONS", 0):
            intervention_details = {"id": "test_id"}

            # 1. First Trigger
            self.engine._intervention_active.clear()
            success = self.engine.start_intervention(intervention_details.copy())
            self.assertTrue(success)
            # Verify tier 1
            self.assertEqual(self.engine._current_intervention_details["tier"], 1)

            # 2. Second Trigger (Immediate)
            self.engine._intervention_active.clear() # Simulate completion
            success = self.engine.start_intervention(intervention_details.copy())
            self.assertTrue(success)
            self.assertEqual(self.engine._current_intervention_details["tier"], 2)

            # 3. Third Trigger (Immediate)
            self.engine._intervention_active.clear()
            success = self.engine.start_intervention(intervention_details.copy())
            self.assertTrue(success)
            self.assertEqual(self.engine._current_intervention_details["tier"], 3)

            # 4. Fourth Trigger (Max Tier Cap)
            self.engine._intervention_active.clear()
            success = self.engine.start_intervention(intervention_details.copy())
            self.assertTrue(success)
            self.assertEqual(self.engine._current_intervention_details["tier"], 3)

    def test_escalation_reset(self):
        with patch("core.intervention_engine.config.MIN_TIME_BETWEEN_INTERVENTIONS", 0):
            intervention_details = {"id": "test_id"}

            # 1. First Trigger
            self.engine._intervention_active.clear()
            self.engine.start_intervention(intervention_details.copy())
            self.assertEqual(self.engine._current_intervention_details["tier"], 1)
            self.engine._intervention_active.clear()

            # Wait for window to pass
            time.sleep(1.1)

            # 2. Second Trigger (Should reset)
            self.engine.start_intervention(intervention_details.copy())
            self.assertEqual(self.engine._current_intervention_details["tier"], 1)

    def test_category_cooldown(self):
        with patch("core.intervention_engine.config.MIN_TIME_BETWEEN_INTERVENTIONS", 0):
            cat = "test_cat"
            cooldown = 1.0
            details = {"id": "test_id", "category": cat, "cooldown": cooldown}

            # 1. First Trigger (Allowed)
            self.engine._intervention_active.clear()
            success = self.engine.start_intervention(details.copy())
            self.assertTrue(success)
            self.engine._intervention_active.clear()

            # 2. Second Trigger (Blocked)
            success = self.engine.start_intervention(details.copy())
            self.assertFalse(success)

            # Wait
            time.sleep(1.1)

            # 3. Third Trigger (Allowed)
            success = self.engine.start_intervention(details.copy())
            self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
