import time
import unittest
from unittest.mock import MagicMock, patch
from collections import deque
from core.intervention_engine import InterventionEngine
import config

class TestInterventionCentralization(unittest.TestCase):
    def setUp(self):
        self.mock_logic_engine = MagicMock()
        self.mock_logic_engine.get_mode.return_value = "active"

        # Patch config values for predictable testing
        self.config_patcher = patch.multiple(
            'config',
            MIN_TIME_BETWEEN_INTERVENTIONS=60,
            REFLEXIVE_WINDOW_COOLDOWN=300,
            ESCALATION_NAG_INTERVAL=5,
            MAX_INTERVENTION_TIER=3
        )
        self.config_patcher.start()

        self.engine = InterventionEngine(self.mock_logic_engine)

        # Mock library to return valid cards by default
        self.engine.library.get_intervention_by_id = MagicMock(side_effect=lambda x: {"id": x, "message": "test", "tier": 1, "sequence": [{"action": "speak", "content": "test"}]} if x else None)

        # Mock sound/speech for execution tests
        self.engine._speak = MagicMock()
        self.engine._play_sound = MagicMock()

        # Disable threaded execution for logic testing (we'll manually invoke if needed)
        self.engine._run_intervention_thread = MagicMock()

    def tearDown(self):
        self.config_patcher.stop()
        self.engine.shutdown()

    def test_voice_command_bypasses_global_cooldown(self):
        """Regression: Verify that voice commands trigger even if global cooldown is active."""
        # 1. Trigger a normal intervention to set global cooldown
        with patch('time.time', return_value=1000):
            result = self.engine.start_intervention({"id": "normal_trigger", "tier": 1}, category="default")
            self.assertTrue(result)
            self.engine._intervention_active.clear()

        # 2. Immediately trigger a voice command (different ID)
        # Should succeed despite global cooldown
        with patch('time.time', return_value=1005): # 5s later, < 60s global cooldown
            result = self.engine.start_intervention({"id": "voice_cmd", "tier": 1}, category="voice_command")
            self.assertTrue(result, "Voice command should bypass global cooldown")

    def test_reflexive_trigger_respects_category_cooldown(self):
        """Regression: Verify that reflexive triggers obey their specific cooldown (when not escalating)."""
        # 1. Trigger reflexive (ID A)
        with patch('time.time', return_value=1000):
            result = self.engine.start_intervention({"id": "reflex_A", "tier": 1}, category="reflexive_window")
            self.assertTrue(result)
            self.engine._intervention_active.clear()

        # 2. Trigger reflexive (ID B) immediately
        # Different ID -> No escalation logic triggered (assuming strict ID match).
        # Falls through to Category Cooldown check.
        with patch('time.time', return_value=1005):
            result = self.engine.start_intervention({"id": "reflex_B", "tier": 1}, category="reflexive_window")
            self.assertFalse(result, "Reflexive trigger B should be blocked by category cooldown set by A")

    def test_escalation_logic_flow(self):
        """
        Verifies that repeated interventions escalate in tier correctly,
        bypassing standard cooldowns if within the nag interval.
        """
        start_time = 1000

        # 1. First Trigger (Tier 1)
        with patch('time.time', return_value=start_time):
            result = self.engine.start_intervention({"id": "test_escalate", "tier": 1}, category="reflexive_window")
            self.assertTrue(result)
            self.assertEqual(self.engine._current_intervention_details["tier"], 1)
            self.engine._intervention_active.clear()

        # 2. Immediate Retry (Within Nag Interval, e.g. 1s later)
        # Should be suppressed
        with patch('time.time', return_value=start_time + 1):
             result = self.engine.start_intervention({"id": "test_escalate", "tier": 1}, category="reflexive_window")
             self.assertFalse(result, "Should be suppressed by nag interval")

        # 3. Retry after Nag Interval (e.g. 6s later)
        # Should succeed AND escalate to Tier 2
        with patch('time.time', return_value=start_time + 6):
             result = self.engine.start_intervention({"id": "test_escalate", "tier": 1}, category="reflexive_window")
             self.assertTrue(result, "Should bypass cooldown due to escalation")
             self.assertEqual(self.engine._current_intervention_details["tier"], 2, "Should escalate to Tier 2")
             self.engine._intervention_active.clear()

        # 4. Retry again (Escalate to Tier 3)
        with patch('time.time', return_value=start_time + 12):
             result = self.engine.start_intervention({"id": "test_escalate", "tier": 1}, category="reflexive_window")
             self.assertTrue(result)
             self.assertEqual(self.engine._current_intervention_details["tier"], 3, "Should escalate to Tier 3")

    def test_sawtooth_escalation_fix(self):
        """
        Verifies that if current tier is 1 and last was 2, we go to 3,
        avoiding 1 -> 2 -> 1 -> 2 oscillation.
        """
        # Manual setup of history
        self.engine.recent_interventions.append({
            "timestamp": 1000,
            "id": "test_oscillation",
            "tier": 2
        })

        with patch('time.time', return_value=1000 + 10): # 10s later (> nag, < escalation window)
            # Input request is Tier 1
            result = self.engine.start_intervention({"id": "test_oscillation", "tier": 1}, category="reflexive_window")

            self.assertTrue(result)
            # Should be Tier 3 (max(1, 2+1))
            self.assertEqual(self.engine._current_intervention_details["tier"], 3)

    def test_escalation_execution_sound(self):
        """Regression: Verify that escalated interventions add sound."""
        # Unmock _run_intervention_thread but call it manually to test logic inside
        # Actually, the logic for adding sound is in _run_intervention_thread.
        # We need to test that logic.

        # We can just copy the logic or test a private method if we refactored.
        # But here let's just use the fact that we mocked it in setUp.
        # We'll create a new instance or unmock for this test.

        # Re-instantiate to get real method
        real_engine = InterventionEngine(self.mock_logic_engine)
        real_engine._run_sequence = MagicMock()
        real_engine._speak = MagicMock()
        real_engine._play_sound = MagicMock()

        # Setup context
        real_engine._current_intervention_details = {
            "id": "test_sound",
            "tier": 2,
            "sequence": [{"action": "speak", "content": "foo"}],
            "type": "test"
        }

        # Run thread logic synchronously
        real_engine._run_intervention_thread()

        # Verify _run_sequence was called with sound
        args, _ = real_engine._run_sequence.call_args
        sequence = args[0]

        self.assertEqual(sequence[0]["action"], "sound")
        self.assertIn("test_tone.wav", sequence[0]["file"])
        self.assertEqual(sequence[1]["action"], "speak")

if __name__ == '__main__':
    unittest.main()
