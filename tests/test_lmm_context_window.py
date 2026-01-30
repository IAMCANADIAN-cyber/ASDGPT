import unittest
from unittest.mock import MagicMock, patch
import json
from core.lmm_interface import LMMInterface

class TestLMMContextWindow(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.lmm = LMMInterface(data_logger=self.mock_logger)

    @patch('requests.post')
    def test_process_data_injects_active_window(self, mock_post):
        # Setup mock response to avoid retry loop failure
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': json.dumps({
                "state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50},
                "suggestion": None
            })}}]
        }
        mock_post.return_value = mock_response

        user_context = {
            "current_mode": "active",
            "active_window": "VS Code - Project.py",
            "sensor_metrics": {"audio_level": 0.1, "video_activity": 5.0}
        }

        self.lmm.process_data(video_data=None, audio_data=None, user_context=user_context)

        # Verify the call
        args, kwargs = mock_post.call_args
        payload = kwargs['json']

        # Extract the user message content
        # payload['messages'] -> list of dicts. Find role='user'.
        user_msg = next(m for m in payload['messages'] if m['role'] == 'user')
        content_list = user_msg['content']
        # content_list -> list of dicts (type='text' or 'image_url')
        text_content = next(c['text'] for c in content_list if c['type'] == 'text')

        self.assertIn("Active Window: VS Code - Project.py", text_content)

    @patch('requests.post')
    def test_process_data_ignores_unknown_window(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': json.dumps({
                "state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50},
                "suggestion": None
            })}}]
        }
        mock_post.return_value = mock_response

        user_context = {
            "current_mode": "active",
            "active_window": "Unknown",
            "sensor_metrics": {"audio_level": 0.1, "video_activity": 5.0}
        }

        self.lmm.process_data(video_data=None, audio_data=None, user_context=user_context)

        # Verify the call
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        user_msg = next(m for m in payload['messages'] if m['role'] == 'user')
        text_content = next(c['text'] for c in user_msg['content'] if c['type'] == 'text')

        self.assertNotIn("Active Window: Unknown", text_content)

if __name__ == '__main__':
    unittest.main()
