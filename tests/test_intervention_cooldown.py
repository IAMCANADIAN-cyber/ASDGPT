import unittest
from unittest.mock import MagicMock
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.intervention_engine import InterventionEngine
import config

class TestInterventionCooldown(unittest.TestCase):
    def setUp(self):
        self.mock_logic_engine = MagicMock()
        self.mock_logic_engine.get_mode.return_value = "active"
        self.mock_app = MagicMock()

        # Initialize engine
        self.engine = InterventionEngine(self.mock_logic_engine, self.mock_app)

        # Override config for testing
        config.MIN_TIME_BETWEEN_INTERVENTIONS = 2 # 2 seconds for test

    def test_cooldown_enforcement(self):
        """Test that interventions are blocked during cooldown period."""
        # 1. Start first intervention (should succeed)
        details = {"type": "test", "message": "First"}
        success = self.engine.start_intervention(details)
        self.assertTrue(success, "First intervention should start")

        # Stop it so we are not blocked by 'active intervention' check
        self.engine.stop_intervention()
        self.engine._intervention_active.clear()

        # 2. Try immediate second intervention (should fail due to cooldown)
        details2 = {"type": "test", "message": "Second"}
        success = self.engine.start_intervention(details2)
        self.assertFalse(success, "Second intervention should be blocked by cooldown")

        # 3. Wait for cooldown to expire
        time.sleep(2.1)

        # 4. Try again (should succeed)
        success = self.engine.start_intervention(details2)
        self.assertTrue(success, "Intervention should succeed after cooldown")

    def test_system_messages_bypass_cooldown(self):
        """Test that system messages bypass the cooldown."""
        # Trigger cooldown
        self.engine.start_intervention({"type": "test", "message": "trigger"})
        self.engine.stop_intervention()
        self.engine._intervention_active.clear()

        # Try system message
        details_sys = {"type": "mode_change_notification", "message": "Mode Changed"}
        success = self.engine.start_intervention(details_sys)
        self.assertTrue(success, "System message should bypass cooldown")

if __name__ == '__main__':
    unittest.main()
