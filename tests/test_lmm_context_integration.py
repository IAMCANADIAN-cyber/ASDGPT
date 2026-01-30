import unittest
from unittest.mock import MagicMock, patch
import json
import core.lmm_interface # To patch config if needed
from core.lmm_interface import LMMInterface

class TestLMMContextIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        # Ensure fallback is disabled to force request
        with patch.object(core.lmm_interface.config, 'LMM_FALLBACK_ENABLED', False):
             self.lmm_interface = LMMInterface(data_logger=self.mock_logger)

    @patch('requests.post')
    def test_active_window_injection(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
                "suggestion": None
            })}}]
        }
        mock_post.return_value = mock_response

        # Call with active window
        user_context = {
            "active_window": "Visual Studio Code - MyProject",
            "sensor_metrics": {},
            "current_mode": "active"
        }

        with patch.object(core.lmm_interface.config, 'LMM_FALLBACK_ENABLED', False):
            self.lmm_interface.process_data(user_context=user_context)

        # Inspect the call args
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_message_content = messages[1]['content']

        # User message content is a list of dicts or string. In LMMInterface it is a list of dicts.
        text_content = ""
        for part in user_message_content:
            if part['type'] == 'text':
                text_content = part['text']
                break

        self.assertIn("Active Window: Visual Studio Code - MyProject", text_content)

    @patch('requests.post')
    def test_active_window_injection_skipped_if_unknown(self, mock_post):
         # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
                "suggestion": None
            })}}]
        }
        mock_post.return_value = mock_response

        # Call with Unknown
        user_context = {
            "active_window": "Unknown",
            "sensor_metrics": {},
            "current_mode": "active"
        }

        with patch.object(core.lmm_interface.config, 'LMM_FALLBACK_ENABLED', False):
            self.lmm_interface.process_data(user_context=user_context)

        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        user_message_content = payload['messages'][1]['content']

        text_content = ""
        for part in user_message_content:
            if part['type'] == 'text':
                text_content = part['text']
                break

        self.assertNotIn("Active Window: Unknown", text_content)

if __name__ == '__main__':
    unittest.main()
