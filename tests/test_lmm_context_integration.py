import pytest
import json
from unittest.mock import MagicMock, patch
from core.lmm_interface import LMMInterface
import core.lmm_interface

@pytest.fixture
def lmm_interface():
    # Mock logger to avoid noise
    mock_logger = MagicMock()
    # Reset config defaults
    with patch.object(core.lmm_interface.config, 'LMM_FALLBACK_ENABLED', False):
        return LMMInterface(data_logger=mock_logger)

@patch('requests.post')
def test_active_window_injection(mock_post, lmm_interface):
    """
    Verifies that the Active Window string is correctly injected into the LMM prompt
    when provided in user_context.
    """
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({
            "state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50},
            "suggestion": None
        })}}]
    }
    mock_post.return_value = mock_response

    # Define context with active window
    user_context = {
        "current_mode": "active",
        "trigger_reason": "periodic_check",
        "active_window": "Visual Studio Code - project.py",
        "sensor_metrics": {}
    }

    # Call process_data
    lmm_interface.process_data(user_context=user_context)

    # Inspect the call to requests.post
    assert mock_post.called
    args, kwargs = mock_post.call_args
    payload = kwargs['json']

    # Extract the user message content
    messages = payload['messages']
    user_content = next(m['content'] for m in messages if m['role'] == 'user')

    # user_content is a list of dicts (text/image)
    text_content = next(item['text'] for item in user_content if item['type'] == 'text')

    # Assertions
    assert "Active Window: Visual Studio Code - project.py" in text_content
    assert "Trigger Reason: periodic_check" in text_content

@patch('requests.post')
def test_active_window_skipped_if_unknown(mock_post, lmm_interface):
    """
    Verifies that 'Active Window' is NOT injected if the value is 'Unknown'.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "{}"}}]
    }
    # Mock validation to pass so we don't error out before check
    lmm_interface._validate_response_schema = MagicMock(return_value=True)
    mock_post.return_value = mock_response

    user_context = {
        "active_window": "Unknown",
        "sensor_metrics": {}
    }

    lmm_interface.process_data(user_context=user_context)

    args, kwargs = mock_post.call_args
    payload = kwargs['json']
    messages = payload['messages']
    user_content = next(m['content'] for m in messages if m['role'] == 'user')
    text_content = next(item['text'] for item in user_content if item['type'] == 'text')

    assert "Active Window:" not in text_content
