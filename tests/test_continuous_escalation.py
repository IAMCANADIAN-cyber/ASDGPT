import unittest
from unittest.mock import MagicMock, patch
import time
from collections import deque
from core.intervention_engine import InterventionEngine
import config

class TestEscalationSequence(unittest.TestCase):
    def setUp(self):
        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()

        # Patch config
        self.config_patcher = patch.multiple(config,
            MIN_TIME_BETWEEN_INTERVENTIONS=0, # Disable global cooldown for this test
            REFLEXIVE_WINDOW_COOLDOWN=0
        )
        self.config_patcher.start()

        # Mock dependencies
        self.sd_patcher = patch('core.intervention_engine.sd', MagicMock())
        self.sd_patcher.start()
        self.wav_patcher = patch('core.intervention_engine.wavfile', MagicMock())
        self.wav_patcher.start()
        self.pil_patcher = patch('core.intervention_engine.Image', MagicMock())
        self.pil_patcher.start()

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)

        # Force escalation window to be large enough
        self.engine.escalation_window = 60

    def tearDown(self):
        self.config_patcher.stop()
        self.sd_patcher.stop()
        self.wav_patcher.stop()
        self.pil_patcher.stop()

    @patch('threading.Thread')
    def test_continuous_escalation(self, mock_thread):
        """
        Verify that repeated Tier 1 triggers escalate to Tier 2, then Tier 3.
        Current behavior might be 1 -> 2 -> 1 -> 2 due to reset logic.
        """
        intervention_id = "test_escalation_seq"

        # Mock Library to return a card
        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 1,
            "description": "Test Escalation",
            "sequence": [{"action": "speak", "content": "Test"}]
        })

        # 1. First Trigger (Tier 1)
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")

        self.assertTrue(success, "First trigger failed")
        tier1 = self.engine._current_intervention_details["tier"]
        self.assertEqual(tier1, 1, "First trigger should be Tier 1")
        self.engine._intervention_active.clear()

        # 2. Second Trigger (Tier 1 requested)
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")

        self.assertTrue(success, "Second trigger failed")
        tier2 = self.engine._current_intervention_details["tier"]
        self.assertEqual(tier2, 2, "Second trigger should escalate to Tier 2")
        self.engine._intervention_active.clear()

        # 3. Third Trigger (Tier 1 requested)
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")

        self.assertTrue(success, "Third trigger failed")
        tier3 = self.engine._current_intervention_details["tier"]

        # This is the assertion that fails with current logic (it gets 1)
        # We want it to be 3.
        self.assertEqual(tier3, 3, f"Third trigger should escalate to Tier 3, got {tier3}")

if __name__ == '__main__':
    unittest.main()
