import unittest
import time
import threading
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.intervention_engine import InterventionEngine
import config

class MockApp:
    def __init__(self):
        self.data_logger = MagicMock()
        self.tray_icon = MagicMock()

class MockLogicEngine:
    def __init__(self):
        self.mode = "active"
    def get_mode(self):
        return self.mode

class TestInterventionPriority(unittest.TestCase):
    def setUp(self):
        self.mock_app = MockApp()
        self.mock_logic = MockLogicEngine()
        self.engine = InterventionEngine(self.mock_logic, self.mock_app)

        # Reset config to defaults for test
        config.MIN_TIME_BETWEEN_INTERVENTIONS = 0 # Disable cooldown for this test

    def tearDown(self):
        self.engine.shutdown()

    def test_priority_preemption(self):
        """
        Test that a higher tier intervention preempts a lower tier one.
        """
        # 1. Start a low tier intervention (Tier 1)
        # We mock the sequence/action to just sleep so it stays active

        low_priority = {
            "type": "low_prio",
            "message": "Low priority message",
            "tier": 1
        }

        # We need to ensure it runs long enough to be preempted
        # We can mock _run_sequence or _speak to block

        stop_event = threading.Event()

        def blocking_action(*args, **kwargs):
            # Simulate a long action that waits for a stop signal or timeout
            count = 0
            while count < 20 and not stop_event.is_set():
                if self.engine._intervention_active.is_set() == False:
                    break
                time.sleep(0.1)
                count += 1

        # Patch _speak to be our blocking action
        with patch.object(self.engine, '_speak', side_effect=blocking_action):

            # Start Tier 1
            started = self.engine.start_intervention(low_priority)
            self.assertTrue(started, "Tier 1 should start")
            self.assertTrue(self.engine._intervention_active.is_set(), "Intervention should be active")

            # Give it a moment to 'start' the thread
            time.sleep(0.1)

            # 2. Try to start a high tier intervention (Tier 3)
            high_priority = {
                "type": "high_prio",
                "message": "URGENT message",
                "tier": 3
            }

            # This should SUCCEED if preemption is implemented
            # Currently it will fail (return False)
            result = self.engine.start_intervention(high_priority)

            # Allow time for threads to swap if successful
            time.sleep(0.2)

            # Cleanup
            stop_event.set()

            if not result:
                self.fail("Tier 3 failed to preempt Tier 1 (start_intervention returned False)")

            # Verify that the active intervention details are now the high priority one
            self.assertEqual(self.engine._current_intervention_details['type'], "high_prio")
            self.assertEqual(self.engine._current_intervention_details['tier'], 3)

if __name__ == '__main__':
    unittest.main()
