
import unittest
import time
import threading
from unittest.mock import MagicMock
from core.intervention_engine import InterventionEngine

class TestInterventionPriority(unittest.TestCase):
    def setUp(self):
        self.mock_logic_engine = MagicMock()
        self.mock_logic_engine.get_mode.return_value = "active"
        self.mock_app = MagicMock()
        self.engine = InterventionEngine(self.mock_logic_engine, self.mock_app)

        # Override cooldown to 0 for testing
        import config
        config.MIN_TIME_BETWEEN_INTERVENTIONS = 0

    def tearDown(self):
        self.engine.shutdown()

    def test_priority_preemption(self):
        """Test that a higher tier intervention preempts a lower tier one."""

        # Start a low tier intervention
        # We make it long running so it's active
        low_tier_details = {
            "type": "low_priority",
            "message": "I am low priority",
            "tier": 1,
            "sequence": [{"action": "wait", "duration": 2.0}]
        }

        started = self.engine.start_intervention(low_tier_details)
        self.assertTrue(started, "Low tier intervention should start")
        self.assertTrue(self.engine._intervention_active.is_set(), "Intervention should be active")

        # Wait a bit
        time.sleep(0.1)

        # Try to start a high tier intervention
        high_tier_details = {
            "type": "high_priority",
            "message": "I am high priority",
            "tier": 2
        }

        # This should succeed and preempt
        preempted = self.engine.start_intervention(high_tier_details)
        self.assertTrue(preempted, "High tier intervention should preempt")

        # Verify the current details match high tier
        self.assertEqual(self.engine._current_intervention_details["type"], "high_priority")

    def test_priority_ignore(self):
        """Test that a lower/equal tier intervention is ignored if active."""

        # Start high tier
        high_tier_details = {
            "type": "high_priority",
            "message": "I am high priority",
            "tier": 2,
            "sequence": [{"action": "wait", "duration": 2.0}]
        }
        self.engine.start_intervention(high_tier_details)
        time.sleep(0.1)

        # Try low tier
        low_tier_details = {
            "type": "low_priority",
            "message": "I am low priority",
            "tier": 1
        }

        started = self.engine.start_intervention(low_tier_details)
        self.assertFalse(started, "Low tier should be ignored")
        self.assertEqual(self.engine._current_intervention_details["type"], "high_priority")

if __name__ == '__main__':
    unittest.main()
