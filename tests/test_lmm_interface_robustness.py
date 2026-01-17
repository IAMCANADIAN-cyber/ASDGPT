import unittest
from unittest.mock import MagicMock, patch
import json
import requests
from core.lmm_interface import LMMInterface

class TestLMMInterface(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.lmm = LMMInterface(data_logger=self.mock_logger)

    @patch('requests.post')
    def test_process_data_success(self, mock_post):
        # Mock successful response
        response_data = {
            "state_estimation": {
                "arousal": 50, "overload": 10, "focus": 80, "energy": 70, "mood": 60
            },
            "visual_context": ["calm"],
            "suggestion": None
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(response_data)}}]
        }
        mock_post.return_value = mock_response

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})
        self.assertIsNotNone(result)
        self.assertEqual(result['state_estimation']['arousal'], 50)

        # Verify response_format was sent
        args, kwargs = mock_post.call_args
        self.assertIn('response_format', kwargs['json'])
        self.assertEqual(kwargs['json']['response_format'], {"type": "json_object"})

    @patch('requests.post')
    def test_process_data_retry_logic(self, mock_post):
        # Mock first two calls failing, third succeeding
        response_data = {
            "state_estimation": {
                "arousal": 50, "overload": 10, "focus": 80, "energy": 70, "mood": 60
            },
            "visual_context": [],
            "suggestion": None
        }

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(response_data)}}]
        }

        # Side effect: Raise exception twice, then return success
        mock_post.side_effect = [
            requests.exceptions.RequestException("Fail 1"),
            requests.exceptions.RequestException("Fail 2"),
            success_response
        ]

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})
        self.assertIsNotNone(result)
        self.assertEqual(mock_post.call_count, 3)

    @patch('requests.post')
    def test_process_data_schema_validation(self, mock_post):
        # Mock response with missing keys
        invalid_data = {
            "state_estimation": {
                "arousal": 50
                # Missing other keys
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(invalid_data)}}]
        }
        mock_post.return_value = mock_response

        # Disable fallback to check that it returns None (or handles it)
        # Note: In the code, if retries fail and fallback is enabled (default), it returns fallback.
        # Let's temporarily disable fallback in config if needed, or check for fallback response.

        # Checking if it returns fallback response (which has _meta['is_fallback'] = True)
        result = self.lmm.process_data(user_context={"sensor_metrics": {}})

        # It should either be None (if fallback disabled) or fallback
        # Since fallback is enabled by default in config:
        self.assertTrue(result.get('_meta', {}).get('is_fallback'))

    def test_validate_response_schema_visual_context(self):
        """Test validation of visual_context type."""
        # Valid case
        valid_data = {
            "state_estimation": {"arousal": 50, "overload": 10, "focus": 80, "energy": 70, "mood": 60},
            "visual_context": ["calm", "reading"],
            "suggestion": None
        }
        self.assertTrue(self.lmm._validate_response_schema(valid_data))

        # Invalid type (string instead of list)
        invalid_data = {
            "state_estimation": {"arousal": 50, "overload": 10, "focus": 80, "energy": 70, "mood": 60},
            "visual_context": "this should be a list",
            "suggestion": None
        }
        self.assertFalse(self.lmm._validate_response_schema(invalid_data))

    def test_clean_json_string(self):
        # Test markdown removal
        dirty_json = "```json\n{\"key\": \"value\"}\n```"
        clean = self.lmm._clean_json_string(dirty_json)
        self.assertEqual(clean, '{"key": "value"}')

        # Test plain code block
        dirty_code = "```\n{\"key\": \"value\"}\n```"
        clean = self.lmm._clean_json_string(dirty_code)
        self.assertEqual(clean, '{"key": "value"}')
