import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestVideoSensorInit(unittest.TestCase):
    def setUp(self):
        # Patching dictionary for sys.modules
        self.modules_to_patch = {
            "cv2": MagicMock(),
            "numpy": MagicMock(),
        }
        self.patcher = patch.dict(sys.modules, self.modules_to_patch)
        self.patcher.start()

        # Configure cv2 mock defaults
        self.mock_cv2 = sys.modules["cv2"]
        self.mock_cv2.data.haarcascades = "/mock/system/path/"
        self.mock_cv2.CascadeClassifier = MagicMock()

        # Reload VideoSensor to use mocked cv2
        if 'sensors.video_sensor' in sys.modules:
            del sys.modules['sensors.video_sensor']
        from sensors.video_sensor import VideoSensor
        self.VideoSensor = VideoSensor

    def tearDown(self):
        self.patcher.stop()
        if 'sensors.video_sensor' in sys.modules:
            del sys.modules['sensors.video_sensor']

    def test_init_loads_cascades_safely(self):
        """Test that initialization attempts to load cascades and handles success."""
        with patch('os.path.exists', return_value=True):
            sensor = self.VideoSensor(camera_index=None)

            # Should try to load face cascade (local or system)
            # And eye cascade (system)

            # Check calls to CascadeClassifier
            # We expect at least one successful load for face and one for eyes if they exist
            self.assertTrue(self.mock_cv2.CascadeClassifier.called)

            # Check if eye_cascade was set
            self.assertIsNotNone(sensor.eye_cascade)

    def test_init_handles_eye_cascade_failure_gracefully(self):
        """Test that initialization doesn't crash if eye cascade is missing."""

        def exists_side_effect(path):
            # Pretend face cascade exists, eye cascade does not
            if "haarcascade_frontalface_default.xml" in path:
                return True
            if "haarcascade_eye.xml" in path:
                return False
            return False

        with patch('os.path.exists', side_effect=exists_side_effect):
            # This should not raise an exception
            sensor = self.VideoSensor(camera_index=None)

            # eye_cascade should be None or handle missing gracefully depending on implementation
            # Current implementation sets it to None first, then tries to load.
            # If load fails (path doesn't exist), it might remain None or be set to empty classifier

            # The duplicated code in the BUGGY implementation actually tries to load it AGAIN
            # using string concatenation which might crash if cv2.data.haarcascades is not what expected,
            # or it simply loads an empty one if not checked.

            # We just want to ensure it doesn't crash during init.
            self.assertIsNone(sensor.cap) # Camera mock

    def test_eye_cascade_loading_efficiency(self):
        """
        Verify that the eye cascade is loaded exactly once when present, preventing redundant IO/initialization.
        """
        with patch('os.path.exists', return_value=True):
            sensor = self.VideoSensor(camera_index=None)

            # We expect:
            # 1 call for face cascade
            # 1 call for eye cascade

            calls = self.mock_cv2.CascadeClassifier.call_args_list

            # Filter for eye cascade calls
            eye_calls = [c for c in calls if "haarcascade_eye.xml" in str(c)]

            self.assertEqual(len(eye_calls), 1, f"Eye cascade should be loaded exactly once. Count: {len(eye_calls)}")

    def test_buffer_size_is_set(self):
        """
        Verify that CV2.CAP_PROP_BUFFERSIZE is set to 1 during initialization.
        This is critical for Eco Mode (Low FPS) to avoid processing old buffered frames.
        """
        # Set buffer size constant on mock
        self.mock_cv2.CAP_PROP_BUFFERSIZE = 38

        # Setup VideoCapture mock
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        self.mock_cv2.VideoCapture.return_value = mock_cap

        with patch('os.path.exists', return_value=True):
            # Initialize with an index so it tries to open camera
            sensor = self.VideoSensor(camera_index=0)

            # Verify VideoCapture was created
            self.mock_cv2.VideoCapture.assert_called_with(0)

            # Verify set was called with (CAP_PROP_BUFFERSIZE, 1)
            mock_cap.set.assert_called_with(self.mock_cv2.CAP_PROP_BUFFERSIZE, 1)
