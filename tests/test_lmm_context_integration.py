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

            # Verify explicit injection
            self.assertIn("Active Window: VS Code - Project ASDGPT", content_text,
                          "The active window title was NOT found in the LMM prompt.")

    def test_active_window_injection_skipped_if_unknown(self):
        """
        Verifies that if active_window is 'Unknown', it is NOT injected into the prompt.
        """
        user_context = {
            "current_mode": "active",
            "trigger_reason": "periodic",
            "active_window": "Unknown",
            "sensor_metrics": { "audio_level": 0.0, "video_activity": 0.0 }
        }

        with patch.object(self.lmm_interface, '_send_request_with_retry') as mock_send:
            mock_send.return_value = {"state_estimation": {}, "suggestion": None}
            self.lmm_interface.process_data(video_data=None, audio_data=None, user_context=user_context)

            self.assertTrue(mock_send.called)
            payload = mock_send.call_args[0][0]
            messages = payload['messages']
            user_message = next(m for m in messages if m['role'] == 'user')
            content_text = next(c['text'] for c in user_message['content'] if c['type'] == 'text')

            # Verify 'Unknown' is NOT injected
            self.assertNotIn("Active Window: Unknown", content_text)

    def test_system_instruction_context_guidance(self):
        """
        Verifies that the SYSTEM_INSTRUCTION_V1 contains guidance on how to interpret
        Active Window context.
        """
        instruction = self.lmm_interface.SYSTEM_INSTRUCTION
        keywords = ["Active Window", "app"]
        found = any(k.lower() in instruction.lower() for k in keywords)

        self.assertTrue(found, "System instruction lacks explicit guidance on 'Active Window'.")

if __name__ == '__main__':
    unittest.main()
