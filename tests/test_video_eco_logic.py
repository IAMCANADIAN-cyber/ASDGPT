import pytest
import numpy as np
import cv2
from sensors.video_sensor import VideoSensor

class TestVideoEcoLogic:
    def test_calculate_activity_history_update(self):
        sensor = VideoSensor(camera_index=None)

        # Frame 1: Black
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)

        # Frame 2: White
        frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 255

        # 1. Initialize sensor (last_frame is None)
        # Calling calculate_raw_activity with update_history=True should set last_frame
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        sensor.calculate_raw_activity(gray1, update_history=True)
        assert sensor.last_frame is not None
        np.testing.assert_array_equal(sensor.last_frame, gray1)

        # 2. Calculate activity with Frame 2, WITHOUT updating history
        # Diff should be max (255)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        activity_no_update = sensor.calculate_raw_activity(gray2, update_history=False)
        assert activity_no_update == 255.0

        # Verify last_frame is STILL Frame 1
        np.testing.assert_array_equal(sensor.last_frame, gray1)

        # 3. Calculate activity with Frame 2, WITH updating history
        activity_update = sensor.calculate_raw_activity(gray2, update_history=True)
        assert activity_update == 255.0

        # Verify last_frame is NOW Frame 2
        np.testing.assert_array_equal(sensor.last_frame, gray2)

    def test_calculate_activity_wrapper(self):
        sensor = VideoSensor(camera_index=None)
        frame1 = np.zeros((200, 200, 3), dtype=np.uint8)
        frame2 = np.ones((200, 200, 3), dtype=np.uint8) * 255

        # Init
        sensor.calculate_activity(frame1, update_history=True)

        # Check no update
        # calculate_activity resizes to 100x100
        val = sensor.calculate_activity(frame2, update_history=False)
        assert val > 0.0 # Normalized, but > 0

        # Ensure underlying last_frame matches frame1 (resized)
        assert sensor.last_frame.shape == (100, 100)
        assert np.mean(sensor.last_frame) == 0.0
