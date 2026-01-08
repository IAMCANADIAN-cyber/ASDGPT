import unittest
from unittest.mock import MagicMock, patch
import sys
import threading

# Use patch.dict to safely mock modules only for this test scope if needed,
# but preferably we rely on installed dependencies for pure logic tests.
# Since we are testing LogicEngine and SystemTray, we need to handle their imports.

class TestDNDMode(unittest.TestCase):
    def setUp(self):
        # Patch pystray to avoid needing a display
        self.pystray_patcher = patch('core.system_tray.pystray')
        self.mock_pystray = self.pystray_patcher.start()

        # Patch PIL to avoid loading images from disk
        self.pil_patcher = patch('core.system_tray.Image')
        self.mock_pil = self.pil_patcher.start()

        # Patch LogicEngine's dependencies if necessary
        # We assume numpy and cv2 are present in the env as they are requirements

        from core.logic_engine import LogicEngine
        from core.system_tray import ACRTrayIcon

        self.logger = MagicMock()
        self.lmm_interface = MagicMock()
        self.audio_sensor = MagicMock()
        self.video_sensor = MagicMock()

        self.logic_engine = LogicEngine(
            audio_sensor=self.audio_sensor,
            video_sensor=self.video_sensor,
            logger=self.logger,
            lmm_interface=self.lmm_interface
        )
        self.intervention_engine = MagicMock()
        self.logic_engine.set_intervention_engine(self.intervention_engine)

        # Mock app for tray
        self.app = MagicMock()
        self.app.logic_engine = self.logic_engine

        # We need to ensure the tray doesn't actually try to load icons
        with patch('core.system_tray.load_image', return_value=MagicMock()):
            self.tray = ACRTrayIcon(self.app)

    def tearDown(self):
        self.pystray_patcher.stop()
        self.pil_patcher.stop()

    def test_set_dnd_mode(self):
        """Test setting DND mode via LogicEngine."""
        self.logic_engine.set_mode("dnd")
        self.assertEqual(self.logic_engine.get_mode(), "dnd")

    def test_dnd_suppresses_intervention(self):
        """Test that DND mode suppresses interventions."""
        self.logic_engine.set_mode("dnd")
        self.logic_engine.lmm_interface.get_intervention_suggestion.return_value = {"id": "test_intervention"}

        # Simulate data presence
        self.logic_engine.last_video_frame = MagicMock()
        self.logic_engine.last_audio_chunk = MagicMock()

        # Trigger LMM analysis
        # We invoke the internal method directly to verify logic,
        # mocking the thread start to run synchronously or just verifying the call arguments.
        # But _trigger_lmm_analysis starts a thread.
        # Let's mock threading.Thread to run the target immediately or capture it.

        with patch('threading.Thread') as mock_thread_class:
            # When thread is started, we want to capture the target and args
            mock_thread_instance = MagicMock()
            mock_thread_class.return_value = mock_thread_instance

            # This calls _trigger_lmm_analysis -> creates thread -> start
            self.logic_engine._trigger_lmm_analysis(allow_intervention=False)

            # Verify thread was created with correct args
            args, kwargs = mock_thread_class.call_args
            target = kwargs.get('target')
            call_args = kwargs.get('args')

            self.assertEqual(target, self.logic_engine._run_lmm_analysis_async)
            self.assertFalse(call_args[1]) # allow_intervention should be False

            # Now manually run the target to verify suppression logic
            # lmm_payload is call_args[0]
            self.logic_engine._run_lmm_analysis_async(call_args[0], allow_intervention=False)

            # Verify start_intervention was NOT called
            self.intervention_engine.start_intervention.assert_not_called()

            # Verify log message
            self.logger.log_info.assert_any_call("Intervention suggested but suppressed due to mode: {'id': 'test_intervention'}")

    def test_dnd_toggle_via_tray(self):
        """Test toggling DND mode via System Tray."""
        # Initial state: Active
        self.logic_engine.set_mode("active")

        # Toggle ON
        self.tray.on_toggle_dnd(None, None)
        self.assertEqual(self.logic_engine.get_mode(), "dnd")

        # Toggle OFF
        self.tray.on_toggle_dnd(None, None)
        self.assertEqual(self.logic_engine.get_mode(), "active")

    def test_dnd_periodic_monitoring(self):
        """Test that DND mode still performs periodic monitoring."""
        self.logic_engine.set_mode("dnd")
        self.logic_engine.lmm_call_interval = 0 # Force immediate check
        self.logic_engine.last_lmm_call_time = 0

        # Mock _trigger_lmm_analysis to verify it's called
        with patch.object(self.logic_engine, '_trigger_lmm_analysis') as mock_trigger:
            self.logic_engine.update()
            mock_trigger.assert_called_with(allow_intervention=False)

if __name__ == '__main__':
    unittest.main()
