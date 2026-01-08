import unittest
import time
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.intervention_engine import InterventionEngine
from core.logic_engine import LogicEngine
from core.data_logger import DataLogger
import config

class MockApp:
    def __init__(self):
        self.data_logger = DataLogger(log_file_path="test_cooldown.log")

class TestInterventionCooldown(unittest.TestCase):
    def setUp(self):
        self.mock_logic = MagicMock(spec=LogicEngine)
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MockApp()
        self.engine = InterventionEngine(self.mock_logic, self.mock_app)

        # Reset last intervention time
        self.engine.last_intervention_time = 0

    def tearDown(self):
        self.engine.shutdown()

    def test_cooldown_enforcement(self):
        """
        Test that interventions are rejected if they occur too soon after the previous one.
        """
        # Set cooldown to 1 second for testing
        with patch('config.MIN_TIME_BETWEEN_INTERVENTIONS', 1):
            # 1. First intervention should succeed
            details = {"type": "test_intervention", "message": "First"}
            result = self.engine.start_intervention(details)
            self.assertTrue(result, "First intervention should succeed")

            # Stop it so we are technically free to start another (except for cooldown)
            self.engine.stop_intervention()

            # 2. Immediate second intervention should fail due to cooldown
            result = self.engine.start_intervention(details)
            self.assertFalse(result, "Immediate second intervention should fail due to cooldown")

            # 3. Wait for cooldown
            time.sleep(1.1)

            # 4. Intervention after cooldown should succeed
            result = self.engine.start_intervention(details)
            self.assertTrue(result, "Intervention after cooldown should succeed")
            self.engine.stop_intervention()

    def test_system_notifications_bypass_cooldown(self):
        """
        Test that system notifications (e.g. error, mode change) bypass the cooldown.
        """
        with patch('config.MIN_TIME_BETWEEN_INTERVENTIONS', 100):
            # 1. Start normal intervention to set last_intervention_time
            self.engine.start_intervention({"type": "normal", "message": "test"})
            self.engine.stop_intervention()

            # 2. Try system notification immediately
            system_details = {"type": "mode_change_notification", "message": "Mode changed"}

            # Note: start_intervention logic for bypassing cooldown checks 'type'
            # Check the implementation:
            # is_system_msg = execution_details["type"] in ["mode_change_notification", "error_notification", "error_notification_spoken"]

            result = self.engine.start_intervention(system_details)
            self.assertTrue(result, "System notification should bypass cooldown")
            self.engine.stop_intervention()

if __name__ == '__main__':
    unittest.main()
