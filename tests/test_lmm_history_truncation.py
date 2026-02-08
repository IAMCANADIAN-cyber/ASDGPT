import unittest
from unittest.mock import MagicMock, patch
import time
from core.lmm_interface import LMMInterface

class TestLMMHistoryTruncation(unittest.TestCase):
    def test_history_window_title_truncation(self):
        """Verify that long window titles in history are truncated."""
        lmm = LMMInterface()

        # Construct a history with a very long title
        long_title = "A" * 200
        truncated_marker = "..."
        expected_len = 50

        now = time.time()
        history = [
            {
                'timestamp': now - 10,
                'active_window': long_title,
                'mode': 'active',
                'face_detected': True,
                'posture': 'neutral',
                'audio_level': 0.1,
                'video_activity': 1.0
            }
        ]

        user_context = {
            'context_history': history,
            'sensor_metrics': {}
        }

        # Mock requests to avoid network calls
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'choices': [{'message': {'content': '{}'}}]
            }

            lmm.process_data(video_data=None, audio_data=None, user_context=user_context)

            # Inspect the prompt sent
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            messages = payload['messages']
            user_content = messages[1]['content']

            # Find the text part
            text_part = ""
            for part in user_content:
                if part['type'] == 'text':
                    text_part = part['text']
                    break

            # Check if the long title is present (it shouldn't be fully present)
            self.assertNotIn(long_title, text_part, "Full long title should not be present")

            # Check if truncated version is present
            # Assuming truncation logic: text[:47] + "..."
            truncated_expected = long_title[:47] + "..."
            self.assertIn(truncated_expected, text_part, "Truncated title should be present")

    def test_current_window_title_truncation(self):
        """Verify that the current active window title is truncated."""
        lmm = LMMInterface()

        long_title = "B" * 200
        user_context = {
            'active_window': long_title,
            'sensor_metrics': {}
        }

        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'choices': [{'message': {'content': '{}'}}]
            }

            lmm.process_data(video_data=None, audio_data=None, user_context=user_context)

            call_args = mock_post.call_args
            payload = call_args[1]['json']
            messages = payload['messages']
            user_content = messages[1]['content']

            text_part = ""
            for part in user_content:
                if part['type'] == 'text':
                    text_part = part['text']
                    break

            self.assertNotIn(long_title, text_part, "Full current long title should not be present")
            # Using 80 as limit for current window
            truncated_expected = long_title[:77] + "..."
            self.assertIn(truncated_expected, text_part, "Truncated current title should be present")

if __name__ == '__main__':
    unittest.main()
