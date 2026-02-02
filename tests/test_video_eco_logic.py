import pytest
import sys
from unittest.mock import MagicMock, patch
import numpy as np
import time

# Mock dependencies before import
sys.modules['cv2'] = MagicMock()
sys.modules['config'] = MagicMock()

# Setup config mocks
import config
config.VIDEO_WAKE_THRESHOLD = 5.0
config.VIDEO_ECO_HEARTBEAT_INTERVAL = 1.0
config.BASELINE_POSTURE = {}
config.CAMERA_INDEX = 0

from sensors.video_sensor import VideoSensor

class TestVideoEcoLogic:
    @pytest.fixture
    def video_sensor(self):
        # Patch init so it doesn't fail on missing camera index or logic
        with patch.object(VideoSensor, '_initialize_camera'):
             sensor = VideoSensor(camera_index=0)

        # Mock face cascade
        sensor.face_cascade = MagicMock()
        sensor.face_cascade.empty.return_value = False

        # Mock calculate_raw_activity to be controllable
        sensor.calculate_raw_activity = MagicMock(return_value=0.0)

        # Inject our known dependencies if needed
        sensor.logger = MagicMock()

        return sensor

    def test_smart_face_check_skips_detection(self, video_sensor):
        """
        Verifies that face detection is skipped when activity is low and
        time since last check is within heartbeat interval.
        """
        # 1. Initial Call: Should run detection (force first run)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        video_sensor.calculate_raw_activity.return_value = 100.0 # High activity
        video_sensor.process_frame(frame)

        assert video_sensor.face_cascade.detectMultiScale.call_count == 1

        # Capture the time of first run
        if hasattr(video_sensor, 'last_face_check_time'):
            last_time = video_sensor.last_face_check_time
        else:
            # Fallback if attribute not implemented yet (test expects to drive implementation)
            last_time = time.time()

        # 2. Second Call: Low Activity, Time < Interval
        # Mock time to be just slightly after first call (e.g., 0.1s later)
        with patch('time.time', return_value=last_time + 0.1):
             video_sensor.calculate_raw_activity.return_value = 1.0 # Low activity (< 5.0)
             video_sensor.process_frame(frame)

        # Should SKIP detection (call count remains 1)
        # Note: Before implementation, this assertion will FAIL (count will be 2)
        assert video_sensor.face_cascade.detectMultiScale.call_count == 1

    def test_smart_face_check_runs_on_motion(self, video_sensor):
        """
        Verifies that face detection runs immediately if activity is high,
        regardless of heartbeat timer.
        """
        # 1. Initial Call
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        video_sensor.calculate_raw_activity.return_value = 100.0
        video_sensor.process_frame(frame)
        video_sensor.face_cascade.detectMultiScale.reset_mock()

        # Get last time
        if hasattr(video_sensor, 'last_face_check_time'):
            last_time = video_sensor.last_face_check_time
        else:
            last_time = time.time()

        # 2. Second Call: High Activity
        with patch('time.time', return_value=last_time + 0.1):
             video_sensor.calculate_raw_activity.return_value = 10.0 # High activity (> 5.0)
             video_sensor.process_frame(frame)

        # Should run detection
        assert video_sensor.face_cascade.detectMultiScale.call_count == 1

    def test_smart_face_check_runs_on_heartbeat(self, video_sensor):
        """
        Verifies that face detection runs if heartbeat interval has passed,
        even if activity is low.
        """
        # 1. Initial Call
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        video_sensor.calculate_raw_activity.return_value = 100.0
        video_sensor.process_frame(frame)
        video_sensor.face_cascade.detectMultiScale.reset_mock()

        # Get last time
        if hasattr(video_sensor, 'last_face_check_time'):
            last_time = video_sensor.last_face_check_time
        else:
            last_time = time.time()

        # 2. Second Call: Low Activity but Time > Interval (1.0s)
        with patch('time.time', return_value=last_time + 1.5):
             video_sensor.calculate_raw_activity.return_value = 1.0 # Low
             video_sensor.process_frame(frame)

        # Should run detection
        assert video_sensor.face_cascade.detectMultiScale.call_count == 1
