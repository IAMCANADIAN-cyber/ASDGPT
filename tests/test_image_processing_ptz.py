import unittest
import numpy as np
import cv2
from core.image_processing import ImageProcessor

class TestImageProcessingPTZ(unittest.TestCase):
    def setUp(self):
        # Create a black image 640x480
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.height, self.width = 480, 640

    def test_crop_no_face(self):
        metrics = {"face_detected": False, "face_locations": []}
        cropped = ImageProcessor.crop_to_subject(self.frame, metrics)
        # Should return full frame or something close
        self.assertTrue(np.array_equal(cropped, self.frame))

    def test_crop_face_center(self):
        # Face at center: 320, 240. Size 100x100.
        # x, y, w, h.
        # x = 320 - 50 = 270
        # y = 240 - 50 = 190
        metrics = {
            "face_detected": True,
            "face_locations": [[270, 190, 100, 100]]
        }

        cropped = ImageProcessor.crop_to_subject(self.frame, metrics)

        # Expected Logic:
        # target_h = h * 4.0 = 400
        # target_w = target_h * (640/480) = 400 * 1.333 = 533
        # Center is 320, 240.
        h, w = cropped.shape[:2]
        # Allow some margin for integer division
        self.assertTrue(390 <= h <= 410, f"Height {h} not near 400")
        self.assertTrue(520 <= w <= 540, f"Width {w} not near 533")

    def test_crop_face_edge(self):
        # Face at top left corner: 0, 0, 100, 100
        metrics = {
            "face_detected": True,
            "face_locations": [[0, 0, 100, 100]]
        }
        cropped = ImageProcessor.crop_to_subject(self.frame, metrics)

        # Center of face: 50, 50
        # target_h = 400, target_w = 533
        # crop_w = 533, crop_h = 400
        # x1 calculation: 50 - 266 = -216 -> max(0, -216) = 0
        # y1 calculation: 50 - 200 = -150 -> max(0, -150) = 0

        h, w = cropped.shape[:2]
        self.assertTrue(390 <= h <= 410, f"Height {h} not near 400")
        self.assertTrue(520 <= w <= 540, f"Width {w} not near 533")

    def test_crop_face_large(self):
        # Face is huge: 300x300
        metrics = {
            "face_detected": True,
            "face_locations": [[100, 100, 300, 300]]
        }
        cropped = ImageProcessor.crop_to_subject(self.frame, metrics)

        # target_h = 300 * 4 = 1200
        # target_w = 1200 * 1.33 = 1600
        # crop_h = min(480, 1200) = 480
        # crop_w = min(640, 1600) = 640

        # Should return full frame
        h, w = cropped.shape[:2]
        self.assertEqual(h, 480)
        self.assertEqual(w, 640)

if __name__ == '__main__':
    unittest.main()
