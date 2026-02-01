import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestVideoSensorConfig(unittest.TestCase):
    def setUp(self):
        # Patching dictionary for sys.modules
        self.modules_to_patch = {
            "cv2": MagicMock(),
            "numpy": MagicMock(),
        }
        self.patcher = patch.dict(sys.modules, self.modules_to_patch)
        self.patcher.start()

        # Configure cv2 mock
        self.mock_cv2 = sys.modules["cv2"]
        self.mock_cv2.CAP_PROP_BUFFERSIZE = 38 # Arbitrary constant

        # Setup VideoCapture mock
        self.mock_cap = MagicMock()
        self.mock_cap.isOpened.return_value = True
        self.mock_cv2.VideoCapture.return_value = self.mock_cap

        # Reload VideoSensor to use mocked cv2
        if 'sensors.video_sensor' in sys.modules:
            del sys.modules['sensors.video_sensor']
        from sensors.video_sensor import VideoSensor
        self.VideoSensor = VideoSensor

    def tearDown(self):
        self.patcher.stop()
        if 'sensors.video_sensor' in sys.modules:
            del sys.modules['sensors.video_sensor']

    def test_buffer_size_optimization(self):
        """Test that CAP_PROP_BUFFERSIZE is set to 1 during initialization."""
        with patch('os.path.exists', return_value=True):
            # initialize with camera_index=0 to trigger _initialize_camera
            sensor = self.VideoSensor(camera_index=0)

            # Verify set was called with BUFFERSIZE and 1
            # We use assertAnyCall in case other properties are set
            self.mock_cap.set.assert_any_call(self.mock_cv2.CAP_PROP_BUFFERSIZE, 1)
