import unittest
from unittest.mock import MagicMock, patch, ANY
import time
import json
import os
import tempfile
import shutil
from collections import deque

from core.intervention_engine import InterventionEngine
import config

class TestInterventionCentralization(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.prefs_file = os.path.join(self.test_dir, "prefs.json")
        self.suppressions_file = os.path.join(self.test_dir, "suppressions.json")

        # Patch config values
        # Global cooldown: 10s
        # Reflexive cooldown: 5s
        # Escalation Nag: 0s (to allow immediate testing of escalation logic)
        self.config_patcher = patch.multiple(config,
            PREFERENCES_FILE=self.prefs_file,
            SUPPRESSIONS_FILE=self.suppressions_file,
            MIN_TIME_BETWEEN_INTERVENTIONS=10,
            REFLEXIVE_WINDOW_COOLDOWN=5,
            ESCALATION_NAG_INTERVAL=0
        )
        self.config_patcher.start()

        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()

        self.sd_patcher = patch('core.intervention_engine.sd', MagicMock())
        self.sd_patcher.start()

        self.wav_patcher = patch('core.intervention_engine.wavfile', MagicMock())
        self.wav_patcher.start()

        self.pil_patcher = patch('core.intervention_engine.Image', MagicMock())
        self.pil_patcher.start()

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)
        # Ensure cooldowns are using patched config (init happened after patch)
        # But wait, config values are read at init. `getattr(config, ...)` works if config is patched.
        # However, `InterventionEngine` reads `getattr` in `__init__`.
        # So we must ensure patch is active before init. Yes, it is.

    def tearDown(self):
        self.config_patcher.stop()
        self.sd_patcher.stop()
        self.wav_patcher.stop()
        self.pil_patcher.stop()
        shutil.rmtree(self.test_dir)

    @patch('threading.Thread')
    def test_voice_command_bypasses_global_cooldown(self, mock_thread):
        """Verify that voice commands trigger even if global cooldown is active."""
        # 1. Trigger a normal intervention to set global cooldown
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "normal", "message": "msg"}, category="default")
        self.assertTrue(success)
        self.engine._intervention_active.clear()

        # 2. Immediately trigger a voice command
        # Should succeed despite global cooldown
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "voice", "message": "cmd"}, category="voice_command")

        self.assertTrue(success, "Voice command should bypass global cooldown")

    @patch('threading.Thread')
    def test_reflexive_trigger_respects_cooldown(self, mock_thread):
        """Verify that reflexive triggers obey their specific cooldown."""
        # 1. Trigger reflexive
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "reflex", "message": "msg"}, category="reflexive_window")
        self.assertTrue(success)
        self.engine._intervention_active.clear()

        # 2. Trigger again immediately
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "reflex", "message": "msg"}, category="reflexive_window")
        self.assertFalse(success, "Reflexive trigger should be blocked by its cooldown")

        # 3. Trigger after cooldown (5s patched)
        self.engine.last_category_trigger_time["reflexive_window"] -= 6
        self.engine.last_intervention_time -= 11 # Also clear global cooldown just in case (though it shouldn't matter if logic is right)

        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "reflex", "message": "msg"}, category="reflexive_window")
        self.assertTrue(success, "Reflexive trigger should work after cooldown")

    @patch('threading.Thread')
    def test_escalation_logic(self, mock_thread):
        """Verify that repeated interventions escalate tier."""
        intervention_id = "test_escalation"

        # Mock library to return a card
        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 1,
            "description": "Test"
        })

        # 1. First trigger (Tier 1 default)
        with patch('threading.Thread'):
            self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")

        self.assertEqual(self.engine._current_intervention_details["tier"], 1)
        self.engine._intervention_active.clear()

        # Reset cooldowns to allow immediate re-trigger for testing escalation
        self.engine.last_intervention_time = 0
        self.engine.last_category_trigger_time["default"] = 0

        # 2. Second trigger immediately (Tier 1 requested)
        # Should execute as Tier 2
        with patch('threading.Thread'):
            self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")

        self.assertEqual(self.engine._current_intervention_details["tier"], 2, "Should escalate to Tier 2")
        self.engine._intervention_active.clear()

        # Reset cooldowns again for third trigger
        self.engine.last_intervention_time = 0
        self.engine.last_category_trigger_time["default"] = 0

        # 3. Third trigger immediately
        # Logic Update: If requested Tier (1) <= Last Tier (2), we assume the previous higher tier failed,
        # so we continue to escalate to Tier 3. This is smarter than resetting to 1.
        with patch('threading.Thread'):
             self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")

        # Expect continued escalation to Tier 3
        self.assertEqual(self.engine._current_intervention_details["tier"], 3)

    @patch('threading.Thread')
    def test_escalation_execution_sound(self, mock_thread):
        """Verify that escalated interventions add sound."""
        intervention_id = "test_sound_escalation"
        seq = [{"action": "speak", "content": "foo"}]

        # Mock library
        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 1,
            "sequence": seq,
            "description": "Test"
        })

        # Mock _run_sequence to capture what is passed
        self.engine._run_sequence = MagicMock()
        self.engine._speak = MagicMock()
        self.engine._play_sound = MagicMock()

        # 1. Trigger Tier 2 directly (simulating escalation or direct call)
        # Note: We pass "tier": 2 in details, which overrides library tier 1
        details = {"id": intervention_id, "tier": 2}

        with patch('threading.Thread') as mock_t:
             # We need to run the target function of the thread to test _run_intervention_thread logic
             self.engine.start_intervention(details, category="default")
             # Manually invoke the target
             self.engine._run_intervention_thread()

        # Check if sound was added
        # _run_sequence called with modified sequence
        args, _ = self.engine._run_sequence.call_args
        executed_seq = args[0]

        # Expect: Sound (chime/test_tone) + Speak
        self.assertEqual(executed_seq[0]["action"], "sound")
        self.assertIn("test_tone.wav", executed_seq[0]["file"])
        self.assertEqual(executed_seq[1]["action"], "speak")

if __name__ == '__main__':
    unittest.main()
