import unittest
from unittest.mock import MagicMock, patch
import time
from core.intervention_engine import InterventionEngine
from core.logic_engine import LogicEngine
import config

class TestInterventionCentralization(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.data_logger = MagicMock()
        self.logic_engine = MagicMock()
        self.logic_engine.get_mode.return_value = "active"

        # Patch config values for predictable testing
        self.config_patcher = patch.multiple('config',
            MIN_TIME_BETWEEN_INTERVENTIONS=0.1, # Shorten global cooldown
            REFLEXIVE_WINDOW_COOLDOWN=5,
            ESCALATION_NAG_INTERVAL=0, # Allow rapid escalation by default
            MAX_INTERVENTION_TIER=3
        )
        self.config_patcher.start()

        self.engine = InterventionEngine(self.logic_engine, self.mock_app)

        # Override cooldowns with small values for testing
        self.engine.category_cooldowns["default"] = 0.1
        self.engine.category_cooldowns["reflexive_window"] = 0.5
        self.engine.category_cooldowns["voice_command"] = 0.1

        # Ensure we start fresh
        self.engine.last_intervention_time = 0
        self.engine.last_category_trigger_time = {}
        self.engine.recent_interventions.clear()

    def tearDown(self):
        self.engine.shutdown()
        self.config_patcher.stop()

    def test_category_cooldowns(self):
        """Verify category-specific cooldowns are respected."""
        # Use ad-hoc payload to avoid library dependency
        payload = {"type": "test_type", "message": "Test message", "tier": 1}

        # First call: Should succeed
        result1 = self.engine.start_intervention(
            payload,
            category="reflexive_window"
        )
        self.assertTrue(result1, "First intervention should succeed")

        # Immediate second call: Should fail due to category cooldown (0.5s)
        result2 = self.engine.start_intervention(
            payload,
            category="reflexive_window"
        )
        self.assertFalse(result2, "Second intervention should be suppressed by category cooldown")

        # Wait for cooldown (> 0.5s AND > global 0.1s)
        time.sleep(0.6)

        # Third call: Should succeed
        result3 = self.engine.start_intervention(
            payload,
            category="reflexive_window"
        )
        self.assertTrue(result3, f"Third intervention should succeed after cooldown. Last int time: {self.engine.last_intervention_time}")

    def test_escalation_logic_monotonic(self):
        """
        Verify monotonic escalation (T1 -> T2 -> T3) instead of sawtooth.
        """
        # Mock library
        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": "nag", "message": "Nag message", "tier": 1
        })

        # 1. Trigger T1
        self.engine.start_intervention({"id": "nag", "tier": 1}, category="default")
        last_intervention = self.engine.recent_interventions[-1]
        self.assertEqual(last_intervention["tier"], 1)

        time.sleep(0.15) # Wait > 0.1 global cooldown

        # 2. Trigger T1 again (should escalate to T2)
        self.engine.start_intervention({"id": "nag", "tier": 1}, category="default")
        last_intervention = self.engine.recent_interventions[-1]
        self.assertEqual(last_intervention["tier"], 2, "Should escalate to Tier 2")

        time.sleep(0.15)

        # 3. Trigger T1 again (should escalate to T3)
        self.engine.start_intervention({"id": "nag", "tier": 1}, category="default")
        last_intervention = self.engine.recent_interventions[-1]
        self.assertEqual(last_intervention["tier"], 3, "Should escalate to Tier 3")

        time.sleep(0.15)

        # 4. Trigger T1 again (should stay T3, assuming MAX_INTERVENTION_TIER=3)
        self.engine.start_intervention({"id": "nag", "tier": 1}, category="default")
        last_intervention = self.engine.recent_interventions[-1]
        self.assertEqual(last_intervention["tier"], 3, "Should stay at Tier 3")

    def test_nag_suppression(self):
        """
        Verify that repeated interventions within ESCALATION_NAG_INTERVAL are suppressed.
        """
        # Patch config specifically for this test to enable Nag
        with patch('config.ESCALATION_NAG_INTERVAL', 2): # 2 seconds nag interval
            # Mock library
            self.engine.library.get_intervention_by_id = MagicMock(return_value={
                "id": "nag_check", "message": "Nag check", "tier": 1
            })

            # 1. Trigger (t=0)
            res1 = self.engine.start_intervention({"id": "nag_check", "tier": 1}, category="default")
            self.assertTrue(res1, "First trigger should succeed")

            time.sleep(0.15) # Wait > global cooldown (0.1)

            # 2. Trigger (t=0.15) -> Should be suppressed by Nag (0.15 < 2)
            res2 = self.engine.start_intervention({"id": "nag_check", "tier": 1}, category="default")
            self.assertFalse(res2, "Second trigger within Nag interval should be suppressed")

            # 3. Trigger Different ID (t=0.3) -> Should succeed (Nag is per ID)
            # Use ad-hoc for different ID
            res3 = self.engine.start_intervention({"type": "other", "message": "msg", "tier": 1}, category="default")
            self.assertTrue(res3, "Different ID should succeed despite Nag on first ID")

            time.sleep(2.0)

            # 4. Trigger (t=2.3) -> Should succeed and Escalate (2.3 > 2 Nag, 2.3 < 60 Window)
            res4 = self.engine.start_intervention({"id": "nag_check", "tier": 1}, category="default")
            self.assertTrue(res4, "Trigger after Nag interval should succeed")
            last_intervention = self.engine.recent_interventions[-1]
            self.assertEqual(last_intervention["tier"], 2, "Should escalate after Nag interval")

    def test_logic_engine_delegation(self):
        """Verify LogicEngine correctly delegates intervention calls."""
        # Use a real LogicEngine with a mocked InterventionEngine
        real_logic = LogicEngine()
        mock_intervention_engine = MagicMock()
        mock_intervention_engine.start_intervention.return_value = True # Simulate success

        real_logic.set_intervention_engine(mock_intervention_engine)
        real_logic.window_sensor = MagicMock()
        real_logic.window_sensor.get_active_window.return_value = "Reddit - Dive into anything" # Distraction

        # Trigger update
        real_logic.update()

        # Verify InterventionEngine was called
        mock_intervention_engine.start_intervention.assert_called_with(
            {"id": "distraction_alert", "tier": 2},
            category="reflexive_window"
        )

        # Verify no local logging calls for "Triggering..." (Hard to assert absence of specific log message easily without spy,
        # but code inspection confirmed removal).

if __name__ == "__main__":
    unittest.main()
