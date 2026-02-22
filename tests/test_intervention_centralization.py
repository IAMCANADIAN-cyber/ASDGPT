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
        self.config_patcher = patch.multiple(config,
            PREFERENCES_FILE=self.prefs_file,
            SUPPRESSIONS_FILE=self.suppressions_file,
            MIN_TIME_BETWEEN_INTERVENTIONS=10,
            REFLEXIVE_WINDOW_COOLDOWN=5,
            ESCALATION_NAG_INTERVAL=0.1,  # Fast for testing
            create=True
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

    def tearDown(self):
        self.config_patcher.stop()
        self.sd_patcher.stop()
        self.wav_patcher.stop()
        self.pil_patcher.stop()
        shutil.rmtree(self.test_dir)

    @patch('threading.Thread')
    def test_voice_command_bypasses_global_cooldown(self, mock_thread):
        """Verify that voice commands trigger even if global cooldown is active."""
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "normal", "message": "msg"}, category="default")
        self.assertTrue(success)
        self.engine._intervention_active.clear()

        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "voice", "message": "cmd"}, category="voice_command")
        self.assertTrue(success, "Voice command should bypass global cooldown")

    @patch('threading.Thread')
    def test_reflexive_trigger_respects_cooldown(self, mock_thread):
        """Verify that reflexive triggers obey their specific cooldown."""
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "reflex", "message": "msg"}, category="reflexive_window")
        self.assertTrue(success)
        self.engine._intervention_active.clear()

        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "reflex", "message": "msg"}, category="reflexive_window")
        self.assertFalse(success, "Reflexive trigger should be blocked by its cooldown")

        # Advance time beyond cooldown (5s)
        # We manually adjust the stored timestamps to simulate time passing
        self.engine.last_category_trigger_time["reflexive_window"] -= 6
        # Also adjust global intervention time to ensure it doesn't block (though category logic applies first)
        self.engine.last_intervention_time -= 11

        with patch('threading.Thread'):
            success = self.engine.start_intervention({"type": "reflex", "message": "msg"}, category="reflexive_window")
        self.assertTrue(success, "Reflexive trigger should work after cooldown")

    @patch('threading.Thread')
    def test_escalation_logic(self, mock_thread):
        """Verify that repeated interventions escalate tier monotonically."""
        intervention_id = "test_escalation"

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

        # Simulate time passing > Nag Interval but < Cooldown (if we were testing bypass)
        # But here we just reset cooldowns to verify tier logic purely
        time.sleep(0.15)
        self.engine.last_intervention_time = 0
        self.engine.last_category_trigger_time["default"] = 0

        # 2. Second trigger immediately (Tier 1 requested) -> Should execute as Tier 2
        with patch('threading.Thread'):
            self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")
        self.assertEqual(self.engine._current_intervention_details["tier"], 2, "Should escalate to Tier 2")
        self.engine._intervention_active.clear()

        # Reset cooldowns again
        time.sleep(0.15)
        self.engine.last_intervention_time = 0
        self.engine.last_category_trigger_time["default"] = 0

        # 3. Third trigger immediately -> Should execute as Tier 3
        with patch('threading.Thread'):
             self.engine.start_intervention({"id": intervention_id, "tier": 1}, category="default")
        self.assertEqual(self.engine._current_intervention_details["tier"], 3, "Should escalate to Tier 3")

    @patch('threading.Thread')
    def test_escalation_execution_sound(self, mock_thread):
        """Verify that escalated interventions add sound."""
        intervention_id = "test_sound_escalation"
        seq = [{"action": "speak", "content": "foo"}]

        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 1,
            "sequence": seq,
            "description": "Test"
        })

        self.engine._run_sequence = MagicMock()
        self.engine._speak = MagicMock()
        self.engine._play_sound = MagicMock()

        # Trigger Tier 2 directly
        details = {"id": intervention_id, "tier": 2}
        with patch('threading.Thread'):
             self.engine.start_intervention(details, category="default")
             self.engine._run_intervention_thread()

        args, _ = self.engine._run_sequence.call_args
        executed_seq = args[0]
        self.assertEqual(executed_seq[0]["action"], "sound")
        self.assertIn("test_tone.wav", executed_seq[0]["file"])
        self.assertEqual(executed_seq[1]["action"], "speak")

    @patch('threading.Thread')
    def test_escalation_bypass_cooldown(self, mock_thread):
        """Verify that escalation bypasses category cooldown but respects nag interval."""
        intervention_id = "test_bypass"

        # Nag interval is 0.1s via setUp config
        # Reflexive cooldown is 5s

        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id, "tier": 1, "description": "Test"
        })

        # 1. Trigger
        with patch('threading.Thread'):
            self.engine.start_intervention({"id": intervention_id}, category="reflexive_window")
        self.engine._intervention_active.clear()

        # 2. Trigger immediately (delta < nag) -> Should fail
        # No time sleep, so delta is ~0
        with patch('threading.Thread'):
            success = self.engine.start_intervention({"id": intervention_id}, category="reflexive_window")
        self.assertFalse(success, "Should be blocked by nag interval")

        # 3. Trigger after nag (0.2s) but before category cooldown (5s) -> Should succeed & Escalate
        time.sleep(0.2)

        with patch('threading.Thread'):
             success = self.engine.start_intervention({"id": intervention_id}, category="reflexive_window")

        self.assertTrue(success, "Should bypass category cooldown due to escalation")
        self.assertEqual(self.engine._current_intervention_details["tier"], 2)

if __name__ == '__main__':
    unittest.main()
