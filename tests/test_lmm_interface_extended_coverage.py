
import pytest
import json
import requests
from unittest.mock import MagicMock, patch, ANY
from core.lmm_interface import LMMInterface
import config

@pytest.fixture
def mock_logger():
    logger = MagicMock()
    # Mock log_level attribute if accessed
    logger.log_level = "DEBUG"
    return logger

@pytest.fixture
def lmm_interface(mock_logger):
    # Ensure config defaults for tests, cleaning up afterwards
    with patch.object(config, 'LMM_FALLBACK_ENABLED', False):
        yield LMMInterface(data_logger=mock_logger)

def test_check_connection_success(lmm_interface):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        assert lmm_interface.check_connection() is True
        mock_get.assert_called_once()

def test_check_connection_failure(lmm_interface):
    with patch('requests.get') as mock_get:
        # Case 1: Exception
        mock_get.side_effect = requests.exceptions.ConnectionError("Fail")
        assert lmm_interface.check_connection() is False

        # Case 2: Non-200 status
        mock_get.side_effect = None
        mock_get.return_value.status_code = 404
        assert lmm_interface.check_connection() is False

def test_validate_response_schema_edge_cases(lmm_interface):
    base_state = {"arousal": 50, "overload": 10, "focus": 80, "energy": 60, "mood": 70}

    # 1. State key missing
    data = {"state_estimation": base_state.copy(), "suggestion": None}
    del data["state_estimation"]["mood"]
    assert lmm_interface._validate_response_schema(data) is False

    # 2. State key not a number
    data = {"state_estimation": base_state.copy(), "suggestion": None}
    data["state_estimation"]["mood"] = "happy"
    assert lmm_interface._validate_response_schema(data) is False

    # 3. State key out of bounds
    data = {"state_estimation": base_state.copy(), "suggestion": None}
    data["state_estimation"]["mood"] = 101
    assert lmm_interface._validate_response_schema(data) is False

    # 4. Visual context not a list
    data = {"state_estimation": base_state, "visual_context": "bad", "suggestion": None}
    assert lmm_interface._validate_response_schema(data) is False

    # 5. Visual context list contains non-strings
    data = {"state_estimation": base_state, "visual_context": ["good", 123], "suggestion": None}
    assert lmm_interface._validate_response_schema(data) is False

    # 6. Suggestion not a dict
    data = {"state_estimation": base_state, "suggestion": "bad"}
    assert lmm_interface._validate_response_schema(data) is False

    # 7. Suggestion 'type' is not string
    data = {"state_estimation": base_state, "suggestion": {"type": 123}}
    assert lmm_interface._validate_response_schema(data) is False

    # 8. Suggestion type 'text' missing message
    data = {"state_estimation": base_state, "suggestion": {"type": "text"}}
    assert lmm_interface._validate_response_schema(data) is False

    # 9. Suggestion missing both 'id' and 'type'
    data = {"state_estimation": base_state, "suggestion": {"foo": "bar"}}
    assert lmm_interface._validate_response_schema(data) is False

def test_prompt_construction_full_context(lmm_interface):
    """
    Verifies that all context information (audio/video analysis, alerts, suppressions)
    is correctly formatted into the string passed to the LMM.
    """
    user_context = {
        "current_mode": "work",
        "trigger_reason": "high_stress",
        "sensor_metrics": {
            "audio_level": 0.8,
            "video_activity": 30.0,
            "audio_analysis": {
                "pitch_estimation": 150.0,
                "pitch_variance": 20.0,
                "zcr": 0.1,
                "speech_rate": 2.5,
                "is_speech": True,
                "speech_confidence": 0.9
            },
            "video_analysis": {
                "face_detected": True,
                "face_size_ratio": 0.5,
                "vertical_position": 0.4,
                "posture_state": "slouching",
                "face_roll_angle": 20.0
            }
        },
        "current_state_estimation": {"arousal": 60},
        "suppressed_interventions": ["take_break"],
        "system_alerts": ["Overheating"],
        "preferred_interventions": ["box_breathing"]
    }

    with patch('requests.post') as mock_post:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "state_estimation": {"arousal": 50, "overload": 10, "focus": 80, "energy": 60, "mood": 70},
                "suggestion": None
            })}}]
        }
        mock_post.return_value = mock_response

        lmm_interface.process_data(user_context=user_context)

        # Inspect the payload sent
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_msg = messages[1]['content'][0]['text']

        # Check for presence of all key info
        assert "Current Mode: work" in user_msg
        assert "Trigger Reason: high_stress" in user_msg
        assert "Audio Level (RMS): 0.8000" in user_msg

        # Audio Analysis
        assert "Audio Pitch (est): 150.00 Hz" in user_msg
        assert "Speech Rate: 2.50 syllables/sec" in user_msg
        assert "Voice Activity: Yes (Conf: 0.90)" in user_msg

        # Video Analysis
        assert "Face Detected: Yes" in user_msg
        assert "Face Size Ratio: 0.500" in user_msg
        assert "Posture: slouching" in user_msg
        assert "Head Tilt: 20.0 deg" in user_msg

        # Other context
        assert "Previous State: {'arousal': 60}" in user_msg
        assert "Suppressed Interventions (Do NOT suggest): take_break" in user_msg
        assert "SYSTEM ALERTS (High Priority): Overheating" in user_msg
        assert "Preferred Interventions (User found these helpful recently): box_breathing" in user_msg

def test_get_fallback_response_logic(lmm_interface):
    # Test loud environment fallback
    ctx_loud = {"sensor_metrics": {"audio_level": 0.6, "video_activity": 0.0}}
    fallback = lmm_interface._get_fallback_response(ctx_loud)
    assert fallback["state_estimation"]["overload"] == 70
    assert "moment of silence" in fallback["suggestion"]["message"]

    # Test high activity fallback
    ctx_active = {"sensor_metrics": {"audio_level": 0.0, "video_activity": 25.0}}
    fallback = lmm_interface._get_fallback_response(ctx_active)
    assert fallback["state_estimation"]["arousal"] == 70
    assert "seem active" in fallback["suggestion"]["message"]

def test_get_intervention_suggestion(lmm_interface):
    assert lmm_interface.get_intervention_suggestion(None) is None

    resp = {"suggestion": {"id": "foo"}}
    assert lmm_interface.get_intervention_suggestion(resp) == {"id": "foo"}

def test_log_debug_variants(mock_logger):
    # Case 1: Logger has log_debug
    lmm = LMMInterface(data_logger=mock_logger)
    lmm._log_debug("test1")
    mock_logger.log_debug.assert_called_with("LMMInterface: test1")

    # Case 2: Logger has no log_debug but has log_level="DEBUG"
    del mock_logger.log_debug
    lmm = LMMInterface(data_logger=mock_logger)
    lmm._log_debug("test2")
    mock_logger.log_info.assert_called_with("LMMInterface-DEBUG: test2")

def test_retry_on_schema_validation_failure(lmm_interface):
    """
    Simulate a case where the LMM returns valid JSON but it fails schema validation.
    The retry logic should trigger.
    """
    base_state = {"arousal": 50, "overload": 10, "focus": 80, "energy": 60, "mood": 70}
    bad_schema = {"state_estimation": base_state.copy()}
    del bad_schema["state_estimation"]["mood"] # Missing key -> Invalid Schema

    good_schema = {"state_estimation": base_state, "suggestion": None}

    with patch('requests.post') as mock_post:
        # First call returns bad schema, second call returns good schema
        bad_response = MagicMock()
        bad_response.status_code = 200
        bad_response.json.return_value = {"choices": [{"message": {"content": json.dumps(bad_schema)}}]}

        good_response = MagicMock()
        good_response.status_code = 200
        good_response.json.return_value = {"choices": [{"message": {"content": json.dumps(good_schema)}}]}

        mock_post.side_effect = [bad_response, good_response]

        with patch('time.sleep'): # skip sleep
            result = lmm_interface.process_data(user_context={"sensor_metrics": {}})

        assert result is not None
        assert mock_post.call_count == 2
