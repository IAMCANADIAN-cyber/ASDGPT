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

    assert result is not None
    assert result["state_estimation"]["arousal"] == 50
    assert result["suggestion"]["id"] == "test_id"
    assert lmm_interface.circuit_failures == 0

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
        result = lmm_interface.process_data(user_context={"sensor_metrics": {}})

    assert result is None
    assert lmm_interface.circuit_failures == 1

def test_circuit_breaker(lmm_interface):
    lmm_interface.circuit_max_failures = 2
    lmm_interface.circuit_failures = 2
    lmm_interface.circuit_open_time = time.time()
    lmm_interface.circuit_cooldown = 60

    # Should not call process logic
    with patch.object(lmm_interface, '_send_request_with_retry') as mock_send:
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
