import unittest
import threading
import time
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.intervention_engine import InterventionEngine
import config

class TestInterventionPriority(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()
        self.mock_app.data_logger = self.mock_logger

        # Reset config to defaults
        config.MIN_TIME_BETWEEN_INTERVENTIONS = 0 # Disable cooldown for testing

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)

    def tearDown(self):
        self.engine.shutdown()

    def test_priority_preemption(self):
        """
        Test that a higher tier intervention preempts a lower tier one.
        """
        print("\nTesting Priority Preemption...")

        # 1. Start a long-running Tier 1 intervention
        # We'll use a custom sequence with a long wait
        tier1_intervention = {
            "type": "tier1_test",
            "message": "Tier 1 running...",
            "tier": 1,
            "sequence": [
                {"action": "wait", "duration": 5}
            ]
        }

        started = self.engine.start_intervention(tier1_intervention)
        self.assertTrue(started, "Tier 1 intervention should start")
        self.assertTrue(self.engine._intervention_active.is_set())

        # Verify it's running
        time.sleep(0.5)
        self.assertTrue(self.engine.intervention_thread.is_alive())

        # 2. Try to start a Tier 2 intervention
        tier2_intervention = {
            "type": "tier2_test",
            "message": "Tier 2 taking over!",
            "tier": 2,
            "sequence": [
                {"action": "speak", "content": "Tier 2 wins"}
            ]
        }

        print("Attempting to start Tier 2 intervention...")
        started_tier2 = self.engine.start_intervention(tier2_intervention)

        # Verification
        if started_tier2:
            print("SUCCESS: Tier 2 started.")
            # Verify the current details updated
            self.assertEqual(self.engine._current_intervention_details["type"], "tier2_test")
            self.assertEqual(self.engine._current_intervention_details["tier"], 2)
        else:
            print("FAILURE: Tier 2 did not start (likely blocked).")
            self.fail("Tier 2 intervention should have preempted Tier 1")

    def test_lower_priority_ignored(self):
        """
        Test that a lower tier intervention is ignored if a higher one is running.
        """
        print("\nTesting Lower Priority Ignored...")

        # 1. Start a Tier 2 intervention
        tier2_intervention = {
            "type": "tier2_test",
            "message": "Tier 2 running...",
            "tier": 2,
            "sequence": [
                {"action": "wait", "duration": 5}
            ]
        }

        self.engine.start_intervention(tier2_intervention)
        time.sleep(0.5)

        # 2. Try to start a Tier 1 intervention
        tier1_intervention = {
            "type": "tier1_test",
            "message": "Tier 1 trying to interrupt...",
            "tier": 1
        }

        print("Attempting to start Tier 1 intervention...")
        started_tier1 = self.engine.start_intervention(tier1_intervention)

        # Verification
        self.assertFalse(started_tier1, "Tier 1 should be ignored when Tier 2 is active")
        self.assertEqual(self.engine._current_intervention_details["tier"], 2, "Current intervention should still be Tier 2")

if __name__ == '__main__':
    unittest.main()
