
import unittest
from unittest.mock import MagicMock, patch
import time
from core.intervention_engine import InterventionEngine
import config

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
        print("\n--- Trigger 1 (T=0) ---")
        success = self.engine.start_intervention(
            {"id": "test_intervention", "type": "test_type", "message": "msg", "tier": 1},
            category="test_category"
        )
        self.assertTrue(success, "First intervention should succeed")
        # Check history instead of current details (thread race condition)
        self.assertEqual(self.engine.recent_interventions[-1]["tier"], 1)

        # 2. Advance time by 15s (Simulate persistence)
        # 15s is < 300s cooldown, but within 60s escalation window
        print("\n--- Trigger 2 (T=15s) - Attempting Escalation ---")

        # We need to manually adjust time.time() or mock it.
        # Since I can't easily mock time.time() inside the class without patching everything,
        # I will manually adjust the engine's tracking variables to simulate time passing relative to NOW.

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

        # EXPECTED FAILURE: Currently this returns False because of category cooldown
        if not success:
            print("FAILURE: Intervention was suppressed by cooldown instead of escalating!")
        else:
            print(f"SUCCESS: Intervention started with Tier {self.engine.recent_interventions[-1]['tier']}")

        self.assertTrue(success, "Escalation should bypass category cooldown")
        self.assertEqual(self.engine.recent_interventions[-1]["tier"], 2, "Should have escalated to Tier 2")

if __name__ == "__main__":
    unittest.main()
