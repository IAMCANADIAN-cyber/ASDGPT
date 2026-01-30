import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface
import config

class TestLMMInterfaceFallback(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.lmm = LMMInterface(data_logger=self.mock_logger)
        # Force fallback enabled to test the logic directly via process_data or internal method
        self.original_fallback_setting = getattr(config, 'LMM_FALLBACK_ENABLED', False)
        config.LMM_FALLBACK_ENABLED = True

    def tearDown(self):
        config.LMM_FALLBACK_ENABLED = self.original_fallback_setting

    def test_smart_fallback_high_audio(self):
        """Test that fallback logic provides a noise reduction suggestion when audio is high."""
        user_context = {
            "sensor_metrics": {
                "audio_level": 0.8, # High
                "video_activity": 0.0
            }
        }

        # We expect the smart fallback to be used.
        # Currently, due to the bug, it likely uses the dumb one returning None.
        response = self.lmm.process_data(user_context=user_context)

        self.assertIsNotNone(response, "Response should not be None in fallback mode")
        self.assertTrue(response.get("_meta", {}).get("is_fallback"), "Should be marked as fallback")

        suggestion = response.get("suggestion")
        self.assertIsNotNone(suggestion, "Should provide a suggestion for high audio")
        # We want to standardize on 'offline_noise_reduction' or at least 'text' with message
        # The current 'smart' code uses 'text', but we plan to change it to 'offline_noise_reduction'.
        # For this test, we accept either, but check for the message content or type.

        msg = suggestion.get("message", "").lower()
        self.assertTrue("loud" in msg or "noise" in msg or suggestion.get("type") == "offline_noise_reduction",
                        f"Suggestion should address noise. Got: {suggestion}")

    def test_smart_fallback_high_video(self):
        """Test that fallback logic provides activity reduction when video activity is high."""
        user_context = {
            "sensor_metrics": {
                "audio_level": 0.0,
                "video_activity": 30.0 # High (>20)
            }
        }

        response = self.lmm.process_data(user_context=user_context)

        self.assertIsNotNone(response)
        suggestion = response.get("suggestion")
        self.assertIsNotNone(suggestion, "Should provide a suggestion for high video activity")

        msg = suggestion.get("message", "").lower()
        self.assertTrue("active" in msg or "settle" in msg or suggestion.get("type") == "offline_activity_reduction",
                        f"Suggestion should address activity. Got: {suggestion}")

    def test_fallback_neutral(self):
        """Test that fallback returns neutral state if no triggers."""
        user_context = {
            "sensor_metrics": {
                "audio_level": 0.1,
                "video_activity": 0.0
            }
        }

        response = self.lmm.process_data(user_context=user_context)
        self.assertIsNotNone(response)
        self.assertIsNone(response.get("suggestion"), "Should have no suggestion for neutral context")

if __name__ == '__main__':
    unittest.main()
