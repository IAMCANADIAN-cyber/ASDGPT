import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.lmm_interface import LMMInterface
import config

class TestLMMPosturePrompt(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.lmm = LMMInterface(data_logger=self.mock_logger)

        # Disable circuit breaker for tests
        self.lmm.circuit_failures = 0
        self.lmm.circuit_open_time = 0

    @patch('requests.post')
    def test_posture_state_in_prompt(self, mock_post):
        """
        Verifies that 'posture_state' from video analysis is included in the LMM prompt context.
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "state_estimation": {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50},
                        "suggestion": None
                    })
                }
            }]
        }
        mock_post.return_value = mock_response

        # Input data with posture state
        user_context = {
            "sensor_metrics": {
                "audio_level": 0.0,
                "video_activity": 0.0,
                "video_analysis": {
                    "face_detected": True,
                    "face_size_ratio": 0.2,
                    "vertical_position": 0.8,
                    "posture_state": "slouching",
                    "face_roll_angle": 0.0
                }
            },
            "current_mode": "active"
        }

        # Run process_data
        self.lmm.process_data(user_context=user_context)

        # Verify request payload
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_message = next(msg for msg in messages if msg['role'] == 'user')
        content_text = next(part['text'] for part in user_message['content'] if part['type'] == 'text')

        # Check for posture info
        print(f"Content sent to LMM:\n{content_text}")
        self.assertIn("Posture: slouching", content_text, "LMM prompt should contain posture state")

    @patch('requests.post')
    def test_head_tilt_in_prompt(self, mock_post):
        """
        Verifies that significant 'face_roll_angle' (Head Tilt) is included in the LMM prompt context.
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "state_estimation": {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50},
                        "suggestion": None
                    })
                }
            }]
        }
        mock_post.return_value = mock_response

        # Input data with head tilt
        user_context = {
            "sensor_metrics": {
                "audio_level": 0.0,
                "video_activity": 0.0,
                "video_analysis": {
                    "face_detected": True,
                    "face_size_ratio": 0.2,
                    "vertical_position": 0.5,
                    "posture_state": "tilted_right",
                    "face_roll_angle": 25.0
                }
            },
            "current_mode": "active"
        }

        # Run process_data
        self.lmm.process_data(user_context=user_context)

        # Verify request payload
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_message = next(msg for msg in messages if msg['role'] == 'user')
        content_text = next(part['text'] for part in user_message['content'] if part['type'] == 'text')

        # Check for tilt info
        print(f"Content sent to LMM:\n{content_text}")
        self.assertIn("Head Tilt: 25.0 degrees", content_text, "LMM prompt should contain head tilt angle if significant")

if __name__ == '__main__':
    unittest.main()
