import pytest
from unittest.mock import MagicMock, patch
import sys
import threading
import time
import cv2

# Import after mocking potentially missing modules
sys.modules["keyboard"] = MagicMock()

from core.intervention_engine import InterventionEngine

class TestRecordVideoLeak:
    @patch('core.intervention_engine.cv2')
    @patch('core.intervention_engine.os')
    def test_record_video_releases_on_exception(self, mock_os, mock_cv2):
        """
        Verifies that cv2.VideoWriter.release() is called even if an exception
        occurs during the recording loop.
        """
        # Set up mocks
        mock_logic_engine = MagicMock()
        mock_app = MagicMock()

        # Simulate a valid video frame
        mock_frame = MagicMock()
        mock_frame.shape = (480, 640, 3)
        mock_logic_engine.last_video_frame = mock_frame

        engine = InterventionEngine(mock_logic_engine, mock_app)
        engine._intervention_active.set()

        # Mock VideoWriter to raise an exception when write() is called
        mock_writer_instance = MagicMock()
        mock_writer_instance.write.side_effect = RuntimeError("Simulated write error")
        mock_cv2.VideoWriter.return_value = mock_writer_instance

        # We don't want the loop to actually wait real time, so let's patch time
        with patch('core.intervention_engine.time.time', side_effect=[0, 0, 10]):
            with patch('core.intervention_engine.time.sleep'):
                # Call _record_video which should trigger the exception, but it is handled and logged
                engine._record_video("Test Details")

        # Verification: The exception should have been caught and logged by the outer try-except,
        # but release() MUST have been called in the finally block of the inner try-finally.
        mock_writer_instance.release.assert_called_once()
        print("\nSUCCESS: VideoWriter was released after an exception.")

if __name__ == "__main__":
    pytest.main([__file__])
