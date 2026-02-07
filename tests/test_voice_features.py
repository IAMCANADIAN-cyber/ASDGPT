
import unittest
import numpy as np
from unittest.mock import MagicMock, patch
import os
import shutil

from core.image_processing import ImageProcessor
from core.voice_interface import VoiceInterface
from core.stt_interface import STTInterface
import config

class TestDigitalPTZ(unittest.TestCase):
    def test_crop_logic(self):
        # Create a dummy frame 100x100
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # Mock face metrics: Face at 50,50 size 20x20
        face_metrics = {
            "face_locations": [(40, 40, 20, 20)] # x, y, w, h
        }

        cropped = ImageProcessor.crop_to_subject(frame, face_metrics)
        self.assertIsNotNone(cropped)

        # Logic says target_h = h * 4.0 = 80
        # target_w = 80 * (100/100) = 80
        # Crop should be around 80x80
        h, w, _ = cropped.shape
        self.assertEqual(h, 80)
        self.assertEqual(w, 80)

class TestVoiceModules(unittest.TestCase):
    def test_voice_interface_structure(self):
        vi = VoiceInterface(logger=MagicMock())
        # Just ensure methods exist and run without crashing on mock
        vi.speak("Test", blocking=False)
        vi.stop()

    def test_stt_interface_structure(self):
        stt = STTInterface(logger=MagicMock())
        # We can't easily test actual recognition without audio file and internet,
        # but we can test handling of empty/none
        res = stt.transcribe(None, 44100)
        self.assertIsNone(res)

        res_empty = stt.transcribe(np.array([]), 44100)
        self.assertIsNone(res_empty)

if __name__ == '__main__':
    unittest.main()
