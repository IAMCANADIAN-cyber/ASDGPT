import unittest
from unittest.mock import MagicMock, patch, ANY
import time
import json
import os
import sys
import tempfile
import shutil
from collections import deque

from core.intervention_engine import InterventionEngine
import config

class TestInterventionEscalation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.prefs_file = os.path.join(self.test_dir, "prefs.json")
        self.suppressions_file = os.path.join(self.test_dir, "suppressions.json")

        # Patch config values
        self.config_patcher = patch.multiple(config,
            PREFERENCES_FILE=self.prefs_file,
            SUPPRESSIONS_FILE=self.suppressions_file,
            MIN_TIME_BETWEEN_INTERVENTIONS=300, # 5 minutes global cooldown
            ESCALATION_NAG_INTERVAL=15,
            MAX_INTERVENTION_TIER=3,
            REFLEXIVE_WINDOW_COOLDOWN=300
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

        self.subprocess_patcher = patch('core.intervention_engine.subprocess.Popen')
        self.mock_popen = self.subprocess_patcher.start()

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)

    def tearDown(self):
        self.config_patcher.stop()
        self.sd_patcher.stop()
        self.wav_patcher.stop()
        self.pil_patcher.stop()
        self.subprocess_patcher.stop()
        shutil.rmtree(self.test_dir)

    @patch('threading.Thread')
    def test_escalation_bypasses_cooldown(self, mock_thread):
        """Verify that escalation bypasses the standard global cooldown."""
        intervention_id = "test_escalation_bypass"

        # Mock library
        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 1,
            "description": "Test"
        })

        # 1. Trigger Tier 1
        success = self.engine.start_intervention({"id": intervention_id}, category="default")
        self.assertTrue(success)
        self.assertEqual(self.engine._current_intervention_details["tier"], 1)

        # Reset active flag
        self.engine._intervention_active.clear()

        # Advance time by 20s (Less than global 300s, More than Nag 15s)
        self.engine.last_intervention_time = time.time() - 20
        # Mocking time.time() is hard here because it's used inside start_intervention multiple times.
        # Instead, we'll manipulate the stored timestamps in the engine relative to real time.

        current_time = time.time()
        # Fix the history timestamp to be 20s ago
        self.engine.recent_interventions[-1]["timestamp"] = current_time - 20
        self.engine.last_intervention_time = current_time - 20
        self.engine.last_category_trigger_time["default"] = current_time - 20

        # 2. Trigger again immediately (simulated 20s later)
        # Should bypass global cooldown (300s) because it's an escalation
        success = self.engine.start_intervention({"id": intervention_id}, category="default")
        self.assertTrue(success, "Escalation should bypass global cooldown")
        self.assertEqual(self.engine._current_intervention_details["tier"], 2, "Should escalate to Tier 2")

    @patch('threading.Thread')
    def test_nag_interval_suppression(self, mock_thread):
        """Verify that escalation is suppressed if within nag interval."""
        intervention_id = "test_nag"

        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 1,
            "description": "Test"
        })

        # 1. Trigger Tier 1
        self.engine.start_intervention({"id": intervention_id}, category="default")
        self.engine._intervention_active.clear()

        # 2. Trigger again too soon (e.g., 5s later, Nag is 15s)
        current_time = time.time()
        self.engine.recent_interventions[-1]["timestamp"] = current_time - 5
        self.engine.last_intervention_time = current_time - 5

        success = self.engine.start_intervention({"id": intervention_id}, category="default")
        self.assertFalse(success, "Should be suppressed by Nag Interval")

    @patch('threading.Thread')
    def test_full_escalation_chain_to_tier_3(self, mock_thread):
        """Verify 1 -> 2 -> 3 escalation flow."""
        intervention_id = "test_chain"
        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 1,
            "description": "Test"
        })

        # T1
        self.engine.start_intervention({"id": intervention_id}, category="default")
        self.assertEqual(self.engine._current_intervention_details["tier"], 1)
        self.engine._intervention_active.clear()

        # T2 (20s later)
        current_time = time.time()
        self.engine.recent_interventions[-1]["timestamp"] = current_time - 20
        self.engine.start_intervention({"id": intervention_id}, category="default")
        self.assertEqual(self.engine._current_intervention_details["tier"], 2)
        self.engine._intervention_active.clear()

        # T3 (20s later)
        self.engine.recent_interventions[-1]["timestamp"] = current_time - 20 # Updating the *latest* entry which is T2
        self.engine.start_intervention({"id": intervention_id}, category="default")
        self.assertEqual(self.engine._current_intervention_details["tier"], 3)
        self.engine._intervention_active.clear()

        # T3 again (Capped at Max 3)
        self.engine.recent_interventions[-1]["timestamp"] = current_time - 20
        self.engine.start_intervention({"id": intervention_id}, category="default")
        self.assertEqual(self.engine._current_intervention_details["tier"], 3)

    @patch('threading.Thread')
    def test_tier_3_visual_alert(self, mock_thread):
        """Verify Tier 3 triggers subprocess visual alert."""
        intervention_id = "test_visual"
        self.engine.library.get_intervention_by_id = MagicMock(return_value={
            "id": intervention_id,
            "tier": 3, # Directly request Tier 3
            "description": "Visual Test"
        })

        # We need to execute the thread target to test _run_intervention_thread
        # So we won't mock threading.Thread for the execution part, but we will mock start()
        # Actually, let's just call _run_intervention_thread directly after setting state.

        self.engine.start_intervention({"id": intervention_id, "tier": 3}, category="default")

        # Manually run the thread logic
        self.engine._run_intervention_thread()

        # Check if subprocess.Popen was called
        self.mock_popen.assert_called()
        args, _ = self.mock_popen.call_args
        cmd_list = args[0]
        self.assertIn("tools/show_alert.py", cmd_list[1])
        self.assertIn("Urgent Alert", cmd_list)

if __name__ == '__main__':
    unittest.main()
