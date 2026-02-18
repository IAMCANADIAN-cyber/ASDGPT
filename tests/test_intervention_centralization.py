import time
import unittest
from unittest.mock import MagicMock, patch
import config

# We need to import the class under test
from core.intervention_engine import InterventionEngine

class TestInterventionCentralization(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_logic_engine = MagicMock()
        self.mock_logic_engine.get_mode.return_value = "active" # Ensure active mode for interventions

        self.mock_app = MagicMock()
        self.mock_app.data_logger = MagicMock()

        # Initialize InterventionEngine
        self.engine = InterventionEngine(self.mock_logic_engine, self.mock_app)

        # Mock external dependencies used in start_intervention
        self.engine.library = MagicMock()
        self.engine.library.get_intervention_by_id.return_value = None # Assume no library card unless specified

        # Ensure clean state
        self.engine.last_intervention_time = 0
        self.engine._intervention_active.clear()
        self.engine.suppressed_interventions = {}

        # Config mocks
        self.original_min_time = config.MIN_TIME_BETWEEN_INTERVENTIONS
        config.MIN_TIME_BETWEEN_INTERVENTIONS = 300 # 5 minutes default

        # Patch time.time to control execution timing
        self.patcher = patch('time.time')
        self.mock_time = self.patcher.start()
        self.mock_time.return_value = 1000.0 # Start at T=1000s

    def tearDown(self):
        config.MIN_TIME_BETWEEN_INTERVENTIONS = self.original_min_time
        self.patcher.stop()

    def test_voice_command_cooldown_override(self):
        """
        Verify that voice commands (category='voice_command') follow their own cooldown (e.g. 5s)
        and ignore the global MIN_TIME_BETWEEN_INTERVENTIONS (300s).
        """
        # 1. Trigger first voice command
        details = {
            "type": "voice_feedback",
            "message": "Taking picture",
            "category": "voice_command",
            "tier": 1
        }

        # Attempt 1: T=1000. Should succeed.
        result1 = self.engine.start_intervention(details)
        self.assertTrue(result1, "First voice command should be allowed.")

        # Simulate wait (e.g., 6 seconds)
        self.mock_time.return_value += 6.0
        self.engine._intervention_active.clear() # Simulate previous intervention finished

        # Attempt 2: T=1006.
        # Global limit (300s) implies T < 1300 -> Fail.
        # Voice limit (5s) implies T > 1005 -> Success.
        # We expect SUCCESS if we implement category-specific cooldowns correctly.

        result2 = self.engine.start_intervention(details)

        # Check assertions
        self.assertTrue(result2, "Second voice command should be allowed after 6s (ignoring global 300s limit).")

    def test_reflexive_cooldown_enforcement(self):
        """
        Verify that reflexive window triggers follow their specific cooldown (300s).
        """
        details = {
            "type": "distraction_alert",
            "message": "Stop that!",
            "category": "reflexive_window",
            "tier": 2
        }

        # Attempt 1: T=1000. Success.
        result1 = self.engine.start_intervention(details)
        self.assertTrue(result1, "First reflexive trigger allowed.")

        # Simulate wait (e.g., 10 seconds)
        self.mock_time.return_value += 10.0
        self.engine._intervention_active.clear()

        # Attempt 2: T=1010.
        # Reflexive cooldown (300s) -> Fail.
        result2 = self.engine.start_intervention(details)
        self.assertFalse(result2, "Reflexive trigger should be blocked by cooldown (10s elapsed < 300s).")

        # Simulate wait (e.g., 300 seconds more -> T=1310)
        self.mock_time.return_value += 300.0

        # Attempt 3: T=1310. Success.
        result3 = self.engine.start_intervention(details)
        self.assertTrue(result3, "Reflexive trigger should be allowed after cooldown expires.")

    def test_global_cooldown_fallback(self):
        """
        Verify that interventions without a specific category fallback to global limit.
        """
        details = {
            "type": "generic_nag",
            "message": "Generic nag",
            # No category -> Should use global
            "tier": 1
        }

        # Attempt 1: T=1000
        self.engine.start_intervention(details)

        # Simulate wait (10s)
        self.mock_time.return_value += 10.0
        self.engine._intervention_active.clear()

        # Attempt 2: T=1010. Global limit 300s -> Fail.
        result2 = self.engine.start_intervention(details)
        self.assertFalse(result2, "Generic intervention should be blocked by global limit.")

if __name__ == '__main__':
    unittest.main()
