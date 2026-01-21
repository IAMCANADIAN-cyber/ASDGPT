import pytest
import json
import time
from unittest.mock import MagicMock, patch
from core.lmm_interface import LMMInterface, LMMResponse
import config
import requests

@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.log_info = MagicMock()
    logger.log_warning = MagicMock()
    logger.log_error = MagicMock()
    logger.log_debug = MagicMock()
    return logger

@pytest.fixture
def lmm_interface(mock_logger):
    # Reset config defaults for tests
    config.LMM_FALLBACK_ENABLED = False
    return LMMInterface(data_logger=mock_logger)

def test_initialization(lmm_interface):
    assert lmm_interface.llm_url.endswith("/v1/chat/completions")
    assert lmm_interface.circuit_failures == 0

def test_validate_response_schema_valid(lmm_interface):
    valid_data = {
        "state_estimation": {
            "arousal": 50, "overload": 10, "focus": 80, "energy": 60, "mood": 70
        },
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(valid_data) is True

def test_validate_response_schema_invalid(lmm_interface):
    invalid_data_missing_key = {
        "state_estimation": {"arousal": 50},
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(invalid_data_missing_key) is False

    invalid_data_bad_type = {
        "state_estimation": "not a dict",
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(invalid_data_bad_type) is False

    invalid_data_out_of_bounds = {
        "state_estimation": {
            "arousal": 150, "overload": 10, "focus": 80, "energy": 60, "mood": 70
        },
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(invalid_data_out_of_bounds) is False

@patch('requests.post')
def test_process_data_success(mock_post, lmm_interface):
    response_content = {
        "state_estimation": {
            "arousal": 50, "overload": 10, "focus": 80, "energy": 60, "mood": 70
        },
        "suggestion": {"id": "test_id"}
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(response_content)}}]
    }
    mock_post.return_value = mock_response

    result = lmm_interface.process_data(user_context={"sensor_metrics": {}})
    assert result.get("suggestion") == {"id": "test_id"}

@patch('requests.post')
def test_process_data_retry_and_fallback(mock_post, lmm_interface):
    # Simulate persistent failure using RequestException
    mock_post.side_effect = requests.exceptions.RequestException("Connection refused")

    # Speed up retry by mocking sleep
    with patch('time.sleep', return_value=None):
        # Fallback is DISABLED by default in test fixture (config.LMM_FALLBACK_ENABLED = False)
        with patch('core.lmm_interface.config.LMM_FALLBACK_ENABLED', False):
            result = lmm_interface.process_data(user_context={"sensor_metrics": {"audio_level": 0.8}})

    assert result is None

    # Now enable it
    with patch('config.LMM_FALLBACK_ENABLED', True):
         # Also patch the fallback method used to ensure it returns what we want
         with patch.object(lmm_interface, '_get_fallback_response', return_value={"fallback": True, "state_estimation": {}}):
             result = lmm_interface.process_data(user_context={"sensor_metrics": {"audio_level": 0.8}})
             assert result is not None
             assert result.get("fallback") is True

@patch('requests.post')
def test_process_data_retry_success(mock_post, lmm_interface):
    # First attempt fails, second succeeds
    response_content = {
        "state_estimation": {
            "arousal": 50, "overload": 10, "focus": 80, "energy": 60, "mood": 70
        },
        "suggestion": None
    }

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(response_content)}}]
    }

    mock_post.side_effect = [requests.exceptions.ConnectionError("Fail"), success_response]

    # Reduce backoff for speed
    with patch('time.sleep', return_value=None):
        result = lmm_interface.process_data(user_context={"sensor_metrics": {}})

    assert result is not None
    assert result["state_estimation"]["arousal"] == 50
    assert mock_post.call_count == 2

@patch('requests.post')
def test_process_data_all_retries_fail(mock_post, lmm_interface):
    mock_post.side_effect = requests.exceptions.ConnectionError("Fail")

    with patch('time.sleep', return_value=None):
        with patch('core.lmm_interface.config.LMM_FALLBACK_ENABLED', False):
            result = lmm_interface.process_data(user_context={"sensor_metrics": {}})

    assert result is None

def test_circuit_breaker(lmm_interface):
    lmm_interface.circuit_max_failures = 2
    lmm_interface.circuit_failures = 2
    lmm_interface.circuit_open_time = time.time()
    lmm_interface.circuit_cooldown = 60

    # Should not call process logic
    with patch.object(lmm_interface, '_send_request_with_retry') as mock_send:
        with patch('core.lmm_interface.config.LMM_FALLBACK_ENABLED', False):
            result = lmm_interface.process_data(user_context={"sensor_metrics": {}})
        assert result is None
        mock_send.assert_not_called()

    # Fast forward time to expire cooldown
    lmm_interface.circuit_open_time = time.time() - 61

    # Should call process logic now
    with patch.object(lmm_interface, '_send_request_with_retry') as mock_send:
        # Mock success to reset circuit
        mock_send.return_value = {"state_estimation": {}, "suggestion": None}
        lmm_interface.process_data(user_context={"sensor_metrics": {}})
        assert lmm_interface.circuit_failures == 0

@patch('requests.post')
def test_fallback_logic(mock_post, lmm_interface):
    config.LMM_FALLBACK_ENABLED = True

    # Make request fail
    mock_post.side_effect = requests.exceptions.ConnectionError("Fail")

    with patch('time.sleep', return_value=None):
        result = lmm_interface.process_data(user_context={"sensor_metrics": {}})

    assert result is not None
    assert result.get("_meta", {}).get("is_fallback") is True
    assert result["state_estimation"]["arousal"] == 50 # Default fallback

# --- NEW TESTS BELOW ---

@patch('requests.get')
def test_check_connection(mock_get, lmm_interface):
    # Success case
    mock_get.return_value.status_code = 200
    assert lmm_interface.check_connection() is True

    # Failure case
    mock_get.return_value.status_code = 404
    assert lmm_interface.check_connection() is False

    # Exception case
    mock_get.side_effect = requests.exceptions.ConnectionError("Fail")
    assert lmm_interface.check_connection() is False

def test_clean_json_string(lmm_interface):
    # Simple JSON
    assert lmm_interface._clean_json_string('{"a": 1}') == '{"a": 1}'

    # Markdown block
    assert lmm_interface._clean_json_string('```json\n{"a": 1}\n```') == '{"a": 1}'

    # Generic block
    assert lmm_interface._clean_json_string('```\n{"a": 1}\n```') == '{"a": 1}'

    # Surrounding text
    # Note: Logic assumes the block is the only content or implementation strips specifically.
    # The current implementation uses regex that strips the markers, but keeps content.
    # If the input is "Text ```json {} ```", it cleans the markers.

    text = '```json\n{"key": "value"}\n```'
    assert lmm_interface._clean_json_string(text) == '{"key": "value"}'

def test_validate_response_schema_edge_cases(lmm_interface):
    # Invalid visual_context type
    invalid_vc = {
        "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
        "visual_context": "not_a_list",
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(invalid_vc) is False

    # Invalid visual_context content
    invalid_vc_content = {
        "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
        "visual_context": [123], # Not strings
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(invalid_vc_content) is False

    # Invalid suggestion type
    invalid_suggestion = {
        "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
        "suggestion": "not_a_dict"
    }
    assert lmm_interface._validate_response_schema(invalid_suggestion) is False

    # Malformed suggestion keys (missing both id and type)
    bad_suggestion_obj = {
        "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
        "suggestion": {"foo": "bar"} # Missing id/type
    }
    assert lmm_interface._validate_response_schema(bad_suggestion_obj) is False
