import unittest
from unittest.mock import MagicMock, patch, ANY
import json
import time
import requests
from core.lmm_interface import LMMInterface, InterventionLibrary
import config

class TestLMMInterfaceCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_library = MagicMock(spec=InterventionLibrary)
        self.mock_library.get_all_interventions_info.return_value = "Mock Interventions"
        self.lmm_interface = LMMInterface(
            data_logger=self.mock_logger,
            intervention_library=self.mock_library
        )
        self.lmm_interface.llm_url = "http://mock-url/v1/chat/completions"

    def test_init_url_handling(self):
        """Test URL handling in __init__"""
        # Test case where URL doesn't end with /v1/chat/completions
        with patch('config.LOCAL_LLM_URL', 'http://base-url/'), \
             patch('core.lmm_interface.config.LOCAL_LLM_URL', 'http://base-url/'):
            lmm = LMMInterface(data_logger=self.mock_logger)
            self.assertEqual(lmm.llm_url, 'http://base-url/v1/chat/completions')

        # Test case where URL already ends with it
        with patch('config.LOCAL_LLM_URL', 'http://base-url/v1/chat/completions'), \
             patch('core.lmm_interface.config.LOCAL_LLM_URL', 'http://base-url/v1/chat/completions'):
            lmm = LMMInterface(data_logger=self.mock_logger)
            self.assertEqual(lmm.llm_url, 'http://base-url/v1/chat/completions')

    def test_log_methods_fallback(self):
        """Test logging methods when no logger is provided (print fallback)"""
        lmm = LMMInterface(data_logger=None, intervention_library=self.mock_library)

        with patch('builtins.print') as mock_print:
            lmm._log_info("test info")
            mock_print.assert_called_with("INFO: LMMInterface: test info")

            lmm._log_warning("test warning")
            mock_print.assert_called_with("WARNING: LMMInterface: test warning")

            lmm._log_error("test error", "details")
            mock_print.assert_called_with("ERROR: LMMInterface: test error | Details: details")

    def test_log_debug_conditions(self):
        """Test _log_debug with different logger configurations"""
        # Case 1: Logger has log_debug
        self.mock_logger.log_debug = MagicMock()
        self.lmm_interface._log_debug("test")
        self.mock_logger.log_debug.assert_called_with("LMMInterface: test")

        # Case 2: Logger has log_level="DEBUG" but no log_debug method
        logger_no_debug = MagicMock()
        del logger_no_debug.log_debug
        logger_no_debug.log_level = "DEBUG"
        lmm = LMMInterface(data_logger=logger_no_debug, intervention_library=self.mock_library)
        lmm._log_debug("test")
        logger_no_debug.log_info.assert_called_with("LMMInterface-DEBUG: test")

    def test_check_connection(self):
        """Test check_connection method"""
        with patch('requests.get') as mock_get:
            # Success case
            mock_get.return_value.status_code = 200
            self.assertTrue(self.lmm_interface.check_connection())

            # Failure case - status code
            mock_get.return_value.status_code = 500
            self.assertFalse(self.lmm_interface.check_connection())

            # Failure case - exception
            mock_get.side_effect = requests.exceptions.RequestException
            self.assertFalse(self.lmm_interface.check_connection())

    def test_validate_response_schema_edge_cases(self):
        """Test validation schema with various invalid inputs"""
        # Not a dict
        self.assertFalse(self.lmm_interface._validate_response_schema([]))

        # Missing state_estimation
        self.assertFalse(self.lmm_interface._validate_response_schema({}))

        # Invalid state_estimation type
        self.assertFalse(self.lmm_interface._validate_response_schema({"state_estimation": "invalid"}))

        # Missing required keys in state
        self.assertFalse(self.lmm_interface._validate_response_schema({"state_estimation": {"arousal": 50}}))

        # Invalid value type in state
        state = {"arousal": "high", "overload": 0, "focus": 0, "energy": 0, "mood": 0}
        self.assertFalse(self.lmm_interface._validate_response_schema({"state_estimation": state}))

        # Value out of bounds
        state = {"arousal": 101, "overload": 0, "focus": 0, "energy": 0, "mood": 0}
        self.assertFalse(self.lmm_interface._validate_response_schema({"state_estimation": state}))

        # Invalid visual_context type
        valid_state = {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50}
        self.assertFalse(self.lmm_interface._validate_response_schema({
            "state_estimation": valid_state,
            "visual_context": "not a list"
        }))

        # visual_context with non-string items
        self.assertFalse(self.lmm_interface._validate_response_schema({
            "state_estimation": valid_state,
            "visual_context": [123]
        }))

    def test_validate_suggestion_schema(self):
        """Test validation of suggestion schema"""
        valid_state = {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50}

        # Suggestion not a dict
        self.assertFalse(self.lmm_interface._validate_response_schema({
            "state_estimation": valid_state,
            "suggestion": "invalid"
        }))

        # Suggestion type not string
        self.assertFalse(self.lmm_interface._validate_response_schema({
            "state_estimation": valid_state,
            "suggestion": {"type": 123}
        }))

        # Suggestion type 'text' missing message
        self.assertFalse(self.lmm_interface._validate_response_schema({
            "state_estimation": valid_state,
            "suggestion": {"type": "text"}
        }))

        # Suggestion missing both id and type
        self.assertFalse(self.lmm_interface._validate_response_schema({
            "state_estimation": valid_state,
            "suggestion": {"other": "value"}
        }))

    def test_clean_json_string(self):
        """Test markdown cleanup"""
        text = "```json\n{\"key\": \"value\"}\n```"
        cleaned = self.lmm_interface._clean_json_string(text)
        self.assertEqual(cleaned, "{\"key\": \"value\"}")

        text = "```\n{\"key\": \"value\"}\n```"
        cleaned = self.lmm_interface._clean_json_string(text)
        self.assertEqual(cleaned, "{\"key\": \"value\"}")

    def test_send_request_with_retry_failures(self):
        """Test retry logic and failure modes"""
        with patch('requests.post') as mock_post:
            # Simulate JSON decode error
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'choices': [{'message': {'content': 'invalid json'}}]
            }

            with self.assertRaises(ValueError) as cm:
                self.lmm_interface._send_request_with_retry({})
            self.assertIn("JSON decode error", str(cm.exception))
            self.assertEqual(mock_post.call_count, 3)

    def test_fallback_response(self):
        """Test fallback response generation with context"""
        # Test loud environment
        context = {'sensor_metrics': {'audio_level': 0.8, 'video_activity': 0}}
        resp = self.lmm_interface._get_fallback_response(context)
        self.assertEqual(resp['state_estimation']['overload'], 70)
        self.assertEqual(resp['suggestion']['message'], "It's quite loud. Maybe take a moment of silence?")

        # Test high activity
        context = {'sensor_metrics': {'audio_level': 0.1, 'video_activity': 25}}
        resp = self.lmm_interface._get_fallback_response(context)
        self.assertEqual(resp['state_estimation']['arousal'], 70)
        self.assertEqual(resp['suggestion']['message'], "You seem active. Remember to breathe.")

    def test_process_data_circuit_breaker(self):
        """Test circuit breaker logic"""
        self.lmm_interface.circuit_failures = self.lmm_interface.circuit_max_failures
        self.lmm_interface.circuit_open_time = time.time()

        # Should fail fast and return None or fallback
        with patch('config.LMM_FALLBACK_ENABLED', False), \
             patch('core.lmm_interface.config.LMM_FALLBACK_ENABLED', False):
            result = self.lmm_interface.process_data(video_data="img")
            self.assertIsNone(result)

        with patch('config.LMM_FALLBACK_ENABLED', True):
            result = self.lmm_interface.process_data(video_data="img")
            self.assertTrue(result['_meta']['is_fallback'])

    def test_process_data_no_input(self):
        """Test process_data with no input"""
        result = self.lmm_interface.process_data()
        self.assertIsNone(result)

    def test_process_data_exception_handling(self):
        """Test exception handling in process_data"""
        with patch('core.lmm_interface.LMMInterface._send_request_with_retry', side_effect=Exception("Fail")):
            with patch('config.LMM_FALLBACK_ENABLED', True):
                result = self.lmm_interface.process_data(video_data="img")
                self.assertTrue(result['_meta']['is_fallback'])
                self.assertEqual(self.lmm_interface.circuit_failures, 1)

    def test_get_intervention_suggestion(self):
        """Test get_intervention_suggestion"""
        self.assertIsNone(self.lmm_interface.get_intervention_suggestion(None))

        suggestion = {"id": "test"}
        data = {"suggestion": suggestion}
        self.assertEqual(self.lmm_interface.get_intervention_suggestion(data), suggestion)

    def test_context_construction(self):
        """Test detailed context string construction"""
        user_context = {
            'current_mode': 'active',
            'trigger_reason': 'test',
            'sensor_metrics': {
                'audio_level': 0.5,
                'video_activity': 10,
                'audio_analysis': {
                    'pitch_estimation': 200,
                    'pitch_variance': 50,
                    'zcr': 0.1,
                    'speech_rate': 4.5,
                    'is_speech': True,
                    'speech_confidence': 0.9
                },
                'video_analysis': {
                    'face_detected': True,
                    'face_size_ratio': 0.1,
                    'vertical_position': 0.5,
                    'posture_state': 'slouching',
                    'face_roll_angle': 20
                }
            },
            'suppressed_interventions': ['int1'],
            'system_alerts': ['alert1'],
            'preferred_interventions': ['int2']
        }

        with patch('core.lmm_interface.LMMInterface._send_request_with_retry') as mock_send:
            mock_send.return_value = {
                "state_estimation": {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50}
            }

            self.lmm_interface.process_data(video_data="img", user_context=user_context)

            # Verify the content string contains expected parts
            call_args = mock_send.call_args[0][0]
            content = call_args['messages'][1]['content'][0]['text']

            self.assertIn("Speech Rate: 4.50", content)
            self.assertIn("Voice Activity: Yes", content)
            self.assertIn("Posture: slouching", content)
            self.assertIn("Head Tilt: 20.0 deg", content)
            self.assertIn("Suppressed Interventions", content)
            self.assertIn("SYSTEM ALERTS", content)
            self.assertIn("Preferred Interventions", content)

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery"""
        self.lmm_interface.circuit_failures = self.lmm_interface.circuit_max_failures
        self.lmm_interface.circuit_open_time = time.time() - (self.lmm_interface.circuit_cooldown + 1)

        with patch('core.lmm_interface.LMMInterface._send_request_with_retry') as mock_send:
            mock_send.return_value = {
                "state_estimation": {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50}
            }

            self.lmm_interface.process_data(video_data="img")

            # Should have reset failures
            self.assertEqual(self.lmm_interface.circuit_failures, 0)
