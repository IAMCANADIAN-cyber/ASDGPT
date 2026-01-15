import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.lmm_interface import LMMInterface

class TestLMMPosturePrompt(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.lmm = LMMInterface(data_logger=self.logger)

    @patch('requests.post')
    def test_prompt_includes_posture_metrics(self, mock_post):
        # Setup successful response
        response_content = {
            "state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50},
            "visual_context": [],
            "suggestion": None
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(response_content)
                }
            }]
        }
        mock_post.return_value = mock_response

        # Input data with significant posture metrics
        user_context = {
            "sensor_metrics": {
                "audio_level": 0.1,
                "video_analysis": {
                    "face_detected": True,
                    "face_size_ratio": 0.2,
                    "vertical_position": 0.5,
                    "face_roll_angle": 25.0, # > 15, should be included
                    "posture_state": "tilted_right" # Not neutral, should be included
                }
            }
        }

        self.lmm.process_data(user_context=user_context)

        # Verify the payload sent to requests.post
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']

        # Find the user message
        user_message = next(m for m in messages if m['role'] == 'user')
        content_parts = user_message['content']
        text_part = next(p for p in content_parts if p['type'] == 'text')
        prompt_text = text_part['text']

        # Assertions
        self.assertIn("Head Tilt: 25.0 degrees", prompt_text)
        self.assertIn("Posture: tilted_right", prompt_text)

    @patch('requests.post')
    def test_prompt_ignores_insignificant_metrics(self, mock_post):
        # Setup successful response
        response_content = {
            "state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50},
            "visual_context": [],
            "suggestion": None
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(response_content)
                }
            }]
        }
        mock_post.return_value = mock_response

        # Input data with insignificant posture metrics
        user_context = {
            "sensor_metrics": {
                "audio_level": 0.1,
                "video_analysis": {
                    "face_detected": True,
                    "face_size_ratio": 0.2,
                    "vertical_position": 0.5,
                    "face_roll_angle": 5.0, # < 15, should NOT be included
                    "posture_state": "neutral" # Neutral, should NOT be included
                }
            }
        }

        self.lmm.process_data(user_context=user_context)

        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_message = next(m for m in messages if m['role'] == 'user')
        text_part = next(p for p in user_message['content'] if p['type'] == 'text')
        prompt_text = text_part['text']

        # Assertions
        self.assertNotIn("Head Tilt:", prompt_text)
        self.assertNotIn("Posture:", prompt_text)

if __name__ == '__main__':
    unittest.main()
