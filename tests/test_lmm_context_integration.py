import unittest
from unittest.mock import MagicMock, patch
import json
import sys

# Mock config properly
mock_config = MagicMock()
mock_config.LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
mock_config.LMM_CIRCUIT_BREAKER_COOLDOWN = 60
mock_config.LOCAL_LLM_URL = "http://localhost:1234"
mock_config.LOCAL_LLM_MODEL_ID = "test-model"

with patch.dict(sys.modules, {'config': mock_config}):
    from core.lmm_interface import LMMInterface
import core.lmm_interface # To patch config if needed
from core.lmm_interface import LMMInterface

class TestLMMContextIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        # Re-patch config during init
        with patch.dict(sys.modules, {'config': mock_config}):
             self.lmm_interface = LMMInterface(data_logger=self.mock_logger)
             self.lmm_interface.circuit_max_failures = 5
             self.lmm_interface.circuit_cooldown = 60

    def test_active_window_injection(self):
        """
        Verifies that 'active_window' from user_context is correctly injected
        into the text prompt passed to _send_request_with_retry.
        """
        user_context = {
            "current_mode": "active",
            "trigger_reason": "periodic",
            "active_window": "VS Code - Project ASDGPT",
            "sensor_metrics": {
                "audio_level": 0.05,
                "video_activity": 0.0,
                "audio_analysis": {},
                "video_analysis": {}
            },
            "current_state_estimation": {},
            "suppressed_interventions": [],
            "preferred_interventions": []
        }

        # Mock the internal method that sends the request
        with patch.object(self.lmm_interface, '_send_request_with_retry') as mock_send:
            # Setup return value
            mock_send.return_value = {
                "state_estimation": {
                    "arousal": 50, "overload": 0, "focus": 80, "energy": 60, "mood": 50
                },
                "visual_context": [],
                "suggestion": None
            }

            self.lmm_interface.process_data(video_data=None, audio_data=None, user_context=user_context)

            self.assertTrue(mock_send.called, "_send_request_with_retry was not called")

            # Inspect the payload passed to the method
            call_args = mock_send.call_args
            payload = call_args[0][0] # First arg is payload

            messages = payload['messages']
            user_message = next(m for m in messages if m['role'] == 'user')
            content_text = next(c['text'] for c in user_message['content'] if c['type'] == 'text')

            print(f"Debug - Injected Prompt Content:\n{content_text}")

            self.assertIn("Active Window: VS Code - Project ASDGPT", content_text,
                          "The active window title was NOT found in the LMM prompt.")

    def test_system_instruction_context_guidance(self):
        """
        Verifies that the SYSTEM_INSTRUCTION_V1 contains guidance on how to interpret
        Active Window context.
        """
        instruction = self.lmm_interface.SYSTEM_INSTRUCTION
        keywords = ["Active Window", "app"]
        found = any(k.lower() in instruction.lower() for k in keywords)

        if not found:
            print("Debug - System Instruction:\n" + instruction)

        self.assertTrue(found, "System instruction lacks explicit guidance on 'Active Window'.")
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

        self.assertIn("Active Window: Unknown", text_content)

if __name__ == '__main__':
    unittest.main()
