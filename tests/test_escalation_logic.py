import unittest
from unittest.mock import MagicMock
from core.intervention_engine import InterventionEngine

class MockLogicEngine:
    def __init__(self):
        self.mode = "active"
    def get_mode(self):
        return self.mode

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
