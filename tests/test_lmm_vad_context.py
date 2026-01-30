import pytest
import json
from unittest.mock import MagicMock, patch
from core.lmm_interface import LMMInterface
import config

@pytest.fixture
def mock_logger():
    logger = MagicMock()
    return logger

@pytest.fixture
def lmm_interface(mock_logger):
    config.LMM_FALLBACK_ENABLED = False
    return LMMInterface(data_logger=mock_logger)

@patch('requests.post')
def test_vad_metrics_in_prompt(mock_post, lmm_interface):
    """
    Verifies that VAD metrics are correctly formatted into the LMM prompt.
    """
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50}, "suggestion": None})}}]
    }
    mock_post.return_value = mock_response

    # Input Context with VAD data
    user_context = {
        "current_mode": "active",
        "trigger_reason": "test_trigger",
        "sensor_metrics": {
            "audio_level": 0.5,
            "video_activity": 10.0,
            "audio_analysis": {
                "pitch_estimation": 150.0,
                "pitch_variance": 20.0,
                "zcr": 0.05,
                "speech_rate": 3.5,
                "is_speech": True,
                "speech_confidence": 0.85
            }
        }
    }

    # Call process_data
    lmm_interface.process_data(user_context=user_context)

    # Inspect the call to requests.post
    assert mock_post.called
    args, kwargs = mock_post.call_args
    payload = kwargs['json']

    # Extract the user message content
    messages = payload['messages']
    user_message_content = messages[1]['content'] # 0 is system, 1 is user

    # The user content is a list of dicts (text, image)
    text_part = user_message_content[0]['text']

    # Assertions
    print(f"\nPrompt Text:\n{text_part}") # For debug if needed

    assert "Audio Pitch (est): 150.00 Hz" in text_part
    assert "Audio Pitch Variance: 20.00" in text_part
    assert "Audio ZCR: 0.0500" in text_part
    assert "Speech Rate: 3.50 syllables/sec" in text_part
    assert "Voice Activity: Yes (Conf: 0.85)" in text_part

@patch('requests.post')
def test_vad_metrics_missing_keys(mock_post, lmm_interface):
    """
    Verifies that the system handles missing VAD keys gracefully (backward compatibility).
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50}, "suggestion": None})}}]
    }
    mock_post.return_value = mock_response

    # Input Context with PARTIAL VAD data
    user_context = {
        "current_mode": "active",
        "sensor_metrics": {
            "audio_level": 0.5,
            "audio_analysis": {
                # Missing speech_rate, is_speech, etc.
                "pitch_estimation": 100.0
            }
        }
    }

    lmm_interface.process_data(user_context=user_context)

    args, kwargs = mock_post.call_args
    payload = kwargs['json']
    text_part = payload['messages'][1]['content'][0]['text']

    # Assertions
    assert "Audio Pitch (est): 100.00 Hz" in text_part
    # Should use defaults for missing keys
    assert "Speech Rate: 0.00 syllables/sec" in text_part
    assert "Voice Activity: No (Conf: 0.00)" in text_part

@patch('requests.post')
def test_no_audio_analysis(mock_post, lmm_interface):
    """
    Verifies behavior when audio_analysis is completely missing.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50}, "suggestion": None})}}]
    }
    mock_post.return_value = mock_response

    user_context = {
        "current_mode": "active",
        "sensor_metrics": {
            "audio_level": 0.5
            # No audio_analysis
        }
    }

    lmm_interface.process_data(user_context=user_context)

    args, kwargs = mock_post.call_args
    payload = kwargs['json']
    text_part = payload['messages'][1]['content'][0]['text']

    # Should NOT contain the specific VAD lines if the dict is missing
    assert "Audio Pitch (est):" not in text_part
    assert "Speech Rate:" not in text_part
