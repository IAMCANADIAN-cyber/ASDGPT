import pytest
from unittest.mock import MagicMock, patch
import sys
import threading
import time

# Mock dependencies that might be imported at top level or during init
sys.modules["keyboard"] = MagicMock()

# Import Application after mocks
from main import Application

class TestShutdownReliability:
    @patch("main.VideoSensor")
    @patch("main.AudioSensor")
    @patch("main.WindowSensor")
    @patch("main.LogicEngine")
    @patch("main.InterventionEngine")
    @patch("main.ACRTrayIcon")
    @patch("main.LMMInterface")
    def test_resources_released_on_crash(
        self,
        MockLMM, MockTray, MockIntervention, MockLogic, MockWindow, MockAudio, MockVideo
    ):
        """
        Verifies that resources ARE released if the main loop crashes (Regression Test).
        """
        # Setup mocks
        mock_video_instance = MockVideo.return_value
        mock_audio_instance = MockAudio.return_value
        mock_logic_instance = MockLogic.return_value

        # Configure LogicEngine to raise an exception during update
        mock_logic_instance.get_mode.return_value = "active"
        mock_logic_instance.update.side_effect = RuntimeError("Simulated Main Loop Crash")

        app = Application()

        with patch("threading.Thread"):
            with pytest.raises(RuntimeError, match="Simulated Main Loop Crash"):
                app.run()

        # Verification:
        # After the fix, _shutdown() should be called in finally block.
        mock_video_instance.release.assert_called()
        mock_audio_instance.release.assert_called()
        print("\nSUCCESS: Resources released correctly after crash.")

if __name__ == "__main__":
    pytest.main([__file__])
