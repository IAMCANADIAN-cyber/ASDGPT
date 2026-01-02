import pytest
import json
import time
import requests
from unittest.mock import Mock, patch
from core.lmm_interface import LMMInterface, StateEstimation, Suggestion

@pytest.fixture
def mock_logger():
    return Mock()

@pytest.fixture
def lmm_interface(mock_logger):
    return LMMInterface(data_logger=mock_logger)

def test_initialization(lmm_interface):
    assert lmm_interface.llm_url is not None
    assert "v1/chat/completions" in lmm_interface.llm_url

def test_validate_response_schema_valid(lmm_interface):
    valid_data = {
        "state_estimation": {
            "arousal": 50,
            "overload": 50,
            "focus": 50,
            "energy": 50,
            "mood": 50
        },
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(valid_data) == True

def test_validate_response_schema_invalid_missing_key(lmm_interface):
    invalid_data = {
        "state_estimation": {
            "arousal": 50
            # missing keys
        },
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(invalid_data) == False

def test_validate_response_schema_invalid_bounds(lmm_interface):
    invalid_data = {
        "state_estimation": {
            "arousal": 150, # Out of bounds
            "overload": 50,
            "focus": 50,
            "energy": 50,
            "mood": 50
        },
        "suggestion": None
    }
    assert lmm_interface._validate_response_schema(invalid_data) == False

@patch('requests.post')
def test_process_data_success(mock_post, lmm_interface):
    expected_response = {
        "state_estimation": {
            "arousal": 60, "overload": 40, "focus": 70, "energy": 60, "mood": 60
        },
        "suggestion": None
    }

    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(expected_response)
            }
        }]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = lmm_interface.process_data(user_context={"sensor_metrics": {}})
    assert result == expected_response

@patch('requests.post')
def test_process_data_retry_and_fallback(mock_post, lmm_interface):
    # Simulate persistent failure using RequestException
    mock_post.side_effect = requests.exceptions.RequestException("Connection refused")

    # Speed up retry by mocking sleep
    with patch('time.sleep', return_value=None):
        # Should return fallback
        result = lmm_interface.process_data(user_context={"sensor_metrics": {"audio_level": 0.8}})

    assert result is not None
    assert result.get("fallback") is True
    # Check fallback logic (loud audio -> high overload)
    assert result["state_estimation"]["overload"] == 70

@patch('requests.post')
def test_process_data_retry_success_after_failure(mock_post, lmm_interface):
    # Simulate 2 failures then success using RequestException

    expected_response = {
        "state_estimation": {
            "arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50
        },
        "suggestion": None
    }

    success_response = Mock()
    success_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(expected_response)
            }
        }]
    }
    success_response.raise_for_status.return_value = None

    # Side effect: Exception, Exception, Success
    # MUST use exceptions that are caught by the retry block
    mock_post.side_effect = [
        requests.exceptions.RequestException("Fail 1"),
        requests.exceptions.RequestException("Fail 2"),
        success_response
    ]

    with patch('time.sleep', return_value=None):
        result = lmm_interface.process_data(user_context={"sensor_metrics": {}})

    assert result == expected_response
    assert mock_post.call_count == 3

def test_fallback_response_logic(lmm_interface):
    # Test loud audio case
    ctx_loud = {"sensor_metrics": {"audio_level": 0.9, "video_activity": 0}}
    res_loud = lmm_interface._fallback_response(ctx_loud)
    assert res_loud["state_estimation"]["overload"] == 70
    assert res_loud["suggestion"]["type"] == "text"

    # Test high activity case
    ctx_active = {"sensor_metrics": {"audio_level": 0.0, "video_activity": 30}}
    res_active = lmm_interface._fallback_response(ctx_active)
    assert res_active["state_estimation"]["arousal"] == 70
    assert res_active["suggestion"]["type"] == "text"

    # Test neutral case
    ctx_neutral = {"sensor_metrics": {"audio_level": 0.0, "video_activity": 0}}
    res_neutral = lmm_interface._fallback_response(ctx_neutral)
    assert res_neutral["state_estimation"]["arousal"] == 50
    assert res_neutral["suggestion"] is None
