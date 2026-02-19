import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import time

from core.intervention_engine import InterventionEngine
import config

class TestInterventionEscalation(unittest.TestCase):
    def setUp(self):
        # Mock Logic Engine
        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"

        # Mock App and Tray Icon
        self.mock_app = MagicMock()
        self.mock_app.tray_icon = MagicMock()
        self.mock_app.data_logger = MagicMock() # To suppress print output

        # Patch dependencies
        self.patchers = []
        self.patchers.append(patch('core.intervention_engine.sd', MagicMock()))
        self.patchers.append(patch('core.intervention_engine.wavfile', MagicMock()))
        self.patchers.append(patch('core.intervention_engine.Image', MagicMock()))
        self.patchers.append(patch('subprocess.Popen', MagicMock()))
        self.patchers.append(patch('threading.Thread')) # Don't actually run threads

        for p in self.patchers:
            p.start()

        self.mock_subprocess = self.patchers[3].new
        self.mock_thread_class = self.patchers[4].new

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)
        self.engine._speak = MagicMock() # Mock internal speak
        self.engine._play_sound = MagicMock()

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    def test_tier_1_notification(self):
        """Tier 1 should trigger tray notification but NOT modal alert."""
        details = {"type": "test_intervention", "message": "Subtle Nudge", "tier": 1}

        self.engine._current_intervention_details = details
        self.engine._run_intervention_thread()

        # Verify Notification
        self.mock_app.tray_icon.notify_user.assert_called_with(
            title="ACR: test_intervention",
            message="Subtle Nudge"
        )

        # Verify NO Subprocess (Tier 1 < 3)
        self.mock_subprocess.assert_not_called()

    def test_tier_2_notification(self):
        """Tier 2 should trigger tray notification but NOT modal alert."""
        details = {"type": "test_intervention", "message": "Moderate Nudge", "tier": 2}
        self.engine._current_intervention_details = details
        self.engine._run_intervention_thread()

        self.mock_app.tray_icon.notify_user.assert_called()
        self.mock_subprocess.assert_not_called()

    def test_tier_3_modal_alert(self):
        """Tier 3 should trigger tray notification AND modal alert."""
        details = {"type": "test_intervention", "message": "URGENT STOP", "tier": 3}
        self.engine._current_intervention_details = details

        # Mock os.path.exists for the tool check
        with patch('os.path.exists', return_value=True):
             self.engine._run_intervention_thread()

        # Verify Notification
        self.mock_app.tray_icon.notify_user.assert_called()

        # Verify Subprocess
        self.mock_subprocess.assert_called()
        call_args = self.mock_subprocess.call_args[0][0] # First arg of call is the command list
        # Check if sys.executable is used
        self.assertEqual(call_args[0], sys.executable)
        self.assertIn("tools/show_alert.py", call_args[1].replace("\\", "/"))
        self.assertIn("URGENT STOP", call_args)

    def test_escalation_logic_flow(self):
        """Verify repeated interventions escalate tier (T1 -> T2 -> T3)."""
        # Disable cooldowns for this test
        self.engine.category_cooldowns["default"] = 0
        with patch.object(config, 'MIN_TIME_BETWEEN_INTERVENTIONS', 0):
            self.engine.recent_interventions.clear()
            self.engine.last_intervention_time = 0

            intervention_id = "test_escalation_id"
            dummy_card = {"id": intervention_id, "tier": 1, "description": "Test", "sequence": []}

            with patch.object(self.engine.library, 'get_intervention_by_id', return_value=dummy_card):
                base_details = {"id": intervention_id, "tier": 1}

                # 1st Call (Tier 1)
                self.engine.start_intervention(base_details.copy())
                self.assertEqual(self.engine._current_intervention_details["tier"], 1)
                self.engine._intervention_active.clear()
                self.engine.last_intervention_time = 0

                # 2nd Call (Should Escalate to Tier 2)
                self.engine.start_intervention(base_details.copy())
                self.assertEqual(self.engine._current_intervention_details["tier"], 2)
                self.engine._intervention_active.clear()
                self.engine.last_intervention_time = 0

                # 3rd Call (Should Escalate to Tier 3)
                self.engine.start_intervention(base_details.copy())

                # Currently expecting 1 due to implementation detail (1 != 2, so reset to 1)
                # If I fix the code, this should be 3.
                # For this step, I will assert what currently happens to prove the test setup is correct.
                # Then I will fix the code and update the test.
                # self.assertEqual(self.engine._current_intervention_details["tier"], 3)

                # Wait, if I want to "Fix" it, I should fix it now.
                # I'll update the expectation to 3, confirm failure, then fix code.
                self.assertEqual(self.engine._current_intervention_details["tier"], 3)

if __name__ == '__main__':
    unittest.main()
