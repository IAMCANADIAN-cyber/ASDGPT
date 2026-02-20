import unittest
from unittest.mock import MagicMock, patch
import time
from core.intervention_engine import InterventionEngine
import config

# From fix-escalation-logic branch
class MockLogicEngine:
    def __init__(self):
        self.mode = "active"
    def get_mode(self):
        return self.mode

# From escalation-cooldown-bypass branch
class TestEscalationFailure(unittest.TestCase):
    def setUp(self):
        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()

        # Patch sounddevice to avoid playing actual sounds
        self.sd_patcher = patch('core.intervention_engine.sd', MagicMock())
        self.sd_patcher.start()

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)
        self.engine.category_cooldowns["test_category"] = 300  # 5 min cooldown

    def tearDown(self):
        self.sd_patcher.stop()

    def test_escalation_blocked_by_cooldown(self):
        # 1. First trigger (Tier 1)
        # print("\n--- Trigger 1 (T=0) ---")
        success = self.engine.start_intervention(
            {"id": "test_intervention", "type": "test_type", "message": "msg", "tier": 1},
            category="test_category"
        )
        self.assertTrue(success, "First intervention should succeed")
        # Check history instead of current details (thread race condition)
        self.assertEqual(self.engine.recent_interventions[-1]["tier"], 1)

        # 2. Advance time by 15s (Simulate persistence)
        # 15s is < 300s cooldown, but within 60s escalation window
        # print("\n--- Trigger 2 (T=15s) - Attempting Escalation ---")

        # Reset the active flag to simulate the first intervention finishing quickly
        self.engine._intervention_active.clear()

        # Trick the engine: Set the last trigger time to 15s ago
        now = time.time()
        self.engine.last_category_trigger_time["test_category"] = now - 15
        self.engine.last_intervention_time = now - 15

        # Also need to adjust the history timestamp for escalation logic
        self.engine.recent_interventions[-1]["timestamp"] = now - 15

        # 3. Second trigger (Should escalate to Tier 2)
        success = self.engine.start_intervention(
            {"id": "test_intervention", "type": "test_type", "message": "msg", "tier": 1},
            category="test_category"
        )

        self.assertTrue(success, "Escalation should bypass category cooldown")
        self.assertEqual(self.engine.recent_interventions[-1]["tier"], 2, "Should have escalated to Tier 2")

# From fix-escalation-logic branch
class TestEscalationLogic(unittest.TestCase):
    def setUp(self):
        self.logic_engine = MockLogicEngine()
        self.engine = InterventionEngine(self.logic_engine)
        # Mock external dependencies to avoid side effects
        self.engine._speak = MagicMock()
        self.engine._play_sound = MagicMock()
        self.engine._show_visual_prompt = MagicMock()
        self.engine.intervention_thread = MagicMock() # Don't spawn real threads
        self.engine._run_intervention_thread = MagicMock()

        # Patch sounddevice if needed (though _play_sound is mocked, import might fail if missing)
        self.sd_patcher = patch('core.intervention_engine.sd', MagicMock())
        self.sd_patcher.start()

        # Bypass nag interval for testing sequence
        self.original_nag = getattr(config, 'ESCALATION_NAG_INTERVAL', 15)
        config.ESCALATION_NAG_INTERVAL = 0

    def tearDown(self):
        self.sd_patcher.stop()
        if hasattr(self, 'original_nag'):
            config.ESCALATION_NAG_INTERVAL = self.original_nag

    def test_escalation_sequence(self):
        """
        Verifies that repeated interventions with the same ID escalate in tier: 1 -> 2 -> 3.
        Current buggy behavior expects 1 -> 2 -> 1.
        """
        intervention_id = "test_intervention"
        category = "test_category"

        # Override cooldowns to allow immediate re-trigger for testing
        self.engine.category_cooldowns[category] = 0
        self.engine.last_intervention_time = 0 # Clear global cooldown

        # 1. First Trigger (Tier 1)
        details_1 = {"id": intervention_id, "type": "test", "message": "msg", "tier": 1}
        success = self.engine.start_intervention(details_1, category=category)
        self.assertTrue(success)

        # Verify recorded tier
        last_entry = self.engine.recent_interventions[-1]
        self.assertEqual(last_entry["tier"], 1, "First trigger should be Tier 1")

        # Reset active flag (simulate intervention finished)
        self.engine._intervention_active.clear()

        # 2. Second Trigger (Input Tier 1) -> Should escalate to Tier 2
        self.engine.last_intervention_time = 0 # Reset global cooldown
        details_2 = {"id": intervention_id, "type": "test", "message": "msg", "tier": 1}
        success = self.engine.start_intervention(details_2, category=category)
        self.assertTrue(success)

        last_entry = self.engine.recent_interventions[-1]
        self.assertEqual(last_entry["tier"], 2, "Second trigger should escalate to Tier 2")

        # Reset active flag
        self.engine._intervention_active.clear()

        # 3. Third Trigger (Input Tier 1) -> Should escalate to Tier 3
        # BUG: Currently reverts to Tier 1 because current(1) != last(2)
        self.engine.last_intervention_time = 0 # Reset global cooldown
        details_3 = {"id": intervention_id, "type": "test", "message": "msg", "tier": 1}
        success = self.engine.start_intervention(details_3, category=category)
        self.assertTrue(success)

        last_entry = self.engine.recent_interventions[-1]

        # This assertion defines the DESIRED behavior
        self.assertEqual(last_entry["tier"], 3, f"Third trigger should escalate to Tier 3, but got {last_entry['tier']}")

if __name__ == "__main__":
    unittest.main()
