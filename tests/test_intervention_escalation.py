import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.intervention_engine import InterventionEngine
import config

class TestInterventionEscalation(unittest.TestCase):
    def setUp(self):
        # Mock LogicEngine and App (not used heavily but required for init)
        self.logic_engine = MagicMock()
        self.logic_engine.get_mode.return_value = "active" # Ensure active mode
        self.app = MagicMock()
        self.app.data_logger = MagicMock()

        # Patch config values for predictable testing
        self.config_patcher = patch.multiple(
            'config',
            MIN_TIME_BETWEEN_INTERVENTIONS=300,
            ESCALATION_NAG_INTERVAL=15,
            MAX_INTERVENTION_TIER=3,
            REFLEXIVE_WINDOW_COOLDOWN=300
        )
        self.config_patcher.start()

        self.engine = InterventionEngine(self.logic_engine, self.app)

        # Override cooldowns with patched values if needed (InterventionEngine reads them at init)
        # But since we patched config *before* init, it should be fine.
        # Double check:
        # self.engine.category_cooldowns['default'] should be 300.

        # Mock blocking methods to prevent threads from hanging and ensure speed
        self.engine.voice_interface.speak = MagicMock()
        self.engine._play_sound = MagicMock()
        self.engine._wait = MagicMock() # Don't wait in tests

    def tearDown(self):
        self.config_patcher.stop()
        self.engine.shutdown()

    @patch('time.time')
    def test_escalation_bypass_global_cooldown(self, mock_time):
        """
        Verify that repeated interventions (Escalation Candidates) bypass the global cooldown
        if enough time (ESCALATION_NAG_INTERVAL) has passed.
        """
        start_time = 1000.0
        mock_time.return_value = start_time

        # 1. First Trigger (Normal)
        # Assuming no prior interventions, global cooldown check passes.
        result = self.engine.start_intervention({"id": "distraction_alert"}, category="reflexive_window")
        self.assertTrue(result, "First intervention should succeed")

        # Verify Tier 2 (default for distraction_alert)
        # We need to peek at internal state or use the mock logger call
        # But start_intervention updates recent_interventions
        self.assertEqual(len(self.engine.recent_interventions), 1)
        self.assertEqual(self.engine.recent_interventions[-1]["id"], "distraction_alert")

        # 2. Second Trigger (Spam Protection)
        # Only 5 seconds later ( < ESCALATION_NAG_INTERVAL=15)
        mock_time.return_value = start_time + 5.0
        result = self.engine.start_intervention({"id": "distraction_alert"}, category="reflexive_window")
        self.assertFalse(result, "Should be suppressed as spam (too soon for escalation)")

        # 3. Third Trigger (Escalation)
        # 20 seconds later ( > ESCALATION_NAG_INTERVAL=15 but < GLOBAL=300)
        mock_time.return_value = start_time + 20.0
        result = self.engine.start_intervention({"id": "distraction_alert"}, category="reflexive_window")
        self.assertTrue(result, "Should succeed as escalation (bypassing global cooldown)")

        # Verify Tier Escalation
        # "distraction_alert" is Tier 2 by default.
        # Escalation logic: min(current + 1, MAX_TIER) -> min(2+1, 3) = 3
        # Wait, the stored tier in recent_interventions[-1] should be 3.
        self.assertEqual(self.engine.recent_interventions[-1]["tier"], 3)

    @patch('time.time')
    @patch('subprocess.Popen')
    def test_tier_3_visual_alert(self, mock_popen, mock_time):
        """
        Verify that a Tier 3 intervention triggers the visual alert via subprocess.
        """
        mock_time.return_value = 1000.0

        # Force a Tier 3 intervention directly
        # "meltdown_prevention" is Tier 3.
        result = self.engine.start_intervention({"id": "meltdown_prevention"}, category="recovery")
        self.assertTrue(result, "Tier 3 intervention should start")

        # Join thread
        if self.engine.intervention_thread:
            self.engine.intervention_thread.join(timeout=2.0)

        # Verify Popen was called
        self.assertTrue(mock_popen.called, "subprocess.Popen should be called for Tier 3")

        # Verify arguments
        if mock_popen.call_args:
            args, _ = mock_popen.call_args
            command_list = args[0]
            # command_list[1] might be show_alert.py depending on how sys.executable is handled
            # command_list should be [sys.executable, "tools/show_alert.py", message]
            found_script = any("tools/show_alert.py" in str(arg) for arg in command_list)
            self.assertTrue(found_script, "tools/show_alert.py not found in subprocess command")

    def test_distraction_alert_exists(self):
        """Verify that 'distraction_alert' is now a valid ID in the library."""
        card = self.engine.library.get_intervention_by_id("distraction_alert")
        self.assertIsNotNone(card, "'distraction_alert' should exist in the library")
        self.assertEqual(card["tier"], 2)

if __name__ == '__main__':
    unittest.main()
