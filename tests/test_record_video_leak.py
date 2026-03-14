import unittest
from unittest.mock import patch, MagicMock

# Ensure config defaults are loaded properly
import config
import time
import sys

# Mock cv2 before importing the engine
sys.modules['cv2'] = MagicMock()

from core.intervention_engine import InterventionEngine

class TestRecordVideoLeak(unittest.TestCase):
    @patch('core.intervention_engine.cv2')
    @patch('time.time')
    def test_record_video_release_on_exception(self, mock_time, mock_cv2):
        # Setup mocks
        mock_logic_engine = MagicMock()
        mock_logic_engine.last_video_frame = MagicMock()
        mock_logic_engine.last_video_frame.shape = (480, 640, 3)

        mock_app = MagicMock()

        engine = InterventionEngine(logic_engine=mock_logic_engine)
        engine.app = mock_app
        # Manually set the active flag to allow recording to loop
        engine._intervention_active.set()

        # Advance time so the loop starts but then we simulate exception
        mock_time.side_effect = [100.0, 100.1, 100.2]

        mock_video_writer = MagicMock()
        mock_cv2.VideoWriter.return_value = mock_video_writer

        # Simulate an exception during out.write
        mock_video_writer.write.side_effect = Exception("Simulated disk error")

        engine._record_video("test details")

        # Verify that release was called despite the exception
        mock_video_writer.release.assert_called_once()

if __name__ == '__main__':
    unittest.main()
