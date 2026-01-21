import unittest
from unittest.mock import MagicMock, patch
import json
import config
from core.lmm_interface import LMMInterface
from core.intervention_library import InterventionLibrary

class TestLMMPromptEngineering(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_library = MagicMock(spec=InterventionLibrary)
        self.mock_library.get_all_interventions_info.return_value = "[Test]: test_id"

        # Patch config values
        self.config_patcher = patch('core.lmm_interface.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.LOCAL_LLM_URL = "http://localhost:1234/v1/chat/completions"
        self.mock_config.LOCAL_LLM_MODEL_ID = "test-model"
        self.mock_config.LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
        self.mock_config.LMM_CIRCUIT_BREAKER_COOLDOWN = 60
        self.mock_config.LMM_FALLBACK_ENABLED = False

        self.lmm_interface = LMMInterface(data_logger=self.mock_logger, intervention_library=self.mock_library)

    def tearDown(self):
        self.config_patcher.stop()

    @patch('requests.post')
    def test_prompt_includes_new_audio_metrics(self, mock_post):
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

        # Define specific metrics
        user_context = {
            "current_mode": "active",
            "trigger_reason": "test",
            "sensor_metrics": {
                "audio_level": 0.3,
                "video_activity": 10.0,
                "audio_analysis": {
                    "pitch_estimation": 150.0,
                    "pitch_variance": 60.0, # High
                    "zcr": 0.15, # High
                    "speech_rate": 6.0, # High
                },
                "video_analysis": {
                    "face_detected": True,
                    "face_size_ratio": 0.1,
                    "vertical_position": 0.5
                }
            }
        }

        # Run process_data
        self.lmm_interface.process_data(user_context=user_context)

        # Inspect the call args
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']

        system_msg = next(m for m in messages if m['role'] == 'system')['content']
        user_msg_parts = next(m for m in messages if m['role'] == 'user')['content']
        user_text = next(p['text'] for p in user_msg_parts if p['type'] == 'text')

        # Check System Prompt updates
        self.assertIn("Audio Pitch Variance: High (>50)", system_msg)
        self.assertIn("Audio ZCR: High (>0.1)", system_msg)
        self.assertIn("Speech Rate: Syllables/sec. High (>4.0)", system_msg)

        # Check User Context injection
        self.assertIn("Audio Pitch (est): 150.00 Hz", user_text)
        self.assertIn("Audio Pitch Variance: 60.00", user_text)
        self.assertIn("Audio ZCR: 0.1500", user_text)
        self.assertIn("Speech Rate: 6.00 syllables/sec", user_text)

    @patch('requests.post')
    def test_prompt_handles_missing_metrics(self, mock_post):
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

        # Missing audio_analysis
        user_context = {
            "current_mode": "active",
            "sensor_metrics": {
                "audio_level": 0.3,
                "video_activity": 10.0
            }
        }

        self.lmm_interface.process_data(user_context=user_context)

        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_msg_parts = next(m for m in messages if m['role'] == 'user')['content']
        user_text = next(p['text'] for p in user_msg_parts if p['type'] == 'text')

        # Should NOT contain the detailed audio lines
        self.assertNotIn("Audio Pitch (est)", user_text)
        self.assertNotIn("Speech Rate", user_text)

if __name__ == '__main__':
    unittest.main()
