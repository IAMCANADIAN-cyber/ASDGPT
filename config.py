import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# --- Helper: Load User Config Override ---
def _load_user_config() -> Dict[str, Any]:
    """Loads user configuration from user_data/config.json if it exists."""
    config_path = os.path.join("user_data", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load user config from {config_path}: {e}")
    return {}

_user_config = _load_user_config()

def _get_conf(key: str, default: Any, cast_type: type = None) -> Any:
    """
    Priority:
    1. Environment Variable (highest for temporary overrides)
    2. user_data/config.json (for persistent user settings)
    3. Default value (codebase default)
    """
    # 1. Environment Variable
    env_val = os.getenv(key)
    if env_val is not None:
        if cast_type:
            try:
                if cast_type == bool:
                    return env_val.lower() in ('true', '1', 'yes')
                return cast_type(env_val)
            except ValueError:
                pass # Fallback
        return env_val

    # 2. User Config
    if key in _user_config:
        val = _user_config[key]
        if cast_type and not isinstance(val, cast_type):
            try:
                return cast_type(val)
            except ValueError:
                pass
        return val

    # 3. Default
    return default

# --- System & Logging ---
APP_NAME = _get_conf("APP_NAME", "ACR")
LOG_LEVEL = _get_conf("LOG_LEVEL", "INFO")
LOG_FILE = _get_conf("LOG_FILE", "acr_app.log")
LOG_MAX_BYTES = _get_conf("LOG_MAX_BYTES", 5 * 1024 * 1024, int) # 5 MB
LOG_BACKUP_COUNT = _get_conf("LOG_BACKUP_COUNT", 5, int)

USER_DATA_DIR = _get_conf("USER_DATA_DIR", "user_data")
SUPPRESSIONS_FILE = os.path.join(USER_DATA_DIR, "suppressions.json")
PREFERENCES_FILE = os.path.join(USER_DATA_DIR, "preferences.json")
EVENTS_FILE = os.path.join(USER_DATA_DIR, "events.jsonl")

# --- Application Mode ---
DEFAULT_MODE = _get_conf("DEFAULT_MODE", "active")
SNOOZE_DURATION = _get_conf("SNOOZE_DURATION", 3600, int)

# --- Hotkeys ---
HOTKEY_CYCLE_MODE = _get_conf("HOTKEY_CYCLE_MODE", "ctrl+alt+m")
HOTKEY_PAUSE_RESUME = _get_conf("HOTKEY_PAUSE_RESUME", "ctrl+alt+p")
HOTKEY_FEEDBACK_HELPFUL = _get_conf("HOTKEY_FEEDBACK_HELPFUL", "ctrl+alt+up")
HOTKEY_FEEDBACK_UNHELPFUL = _get_conf("HOTKEY_FEEDBACK_UNHELPFUL", "ctrl+alt+down")

# --- User Feedback ---
FEEDBACK_WINDOW_SECONDS = _get_conf("FEEDBACK_WINDOW_SECONDS", 15, int)
FEEDBACK_SUPPRESSION_MINUTES = _get_conf("FEEDBACK_SUPPRESSION_MINUTES", 240, int)

# --- Sensors ---
CAMERA_INDEX = _get_conf("CAMERA_INDEX", 0, int)

# Thresholds
AUDIO_THRESHOLD_HIGH = _get_conf("AUDIO_THRESHOLD_HIGH", 0.5, float)
VIDEO_ACTIVITY_THRESHOLD_HIGH = _get_conf("VIDEO_ACTIVITY_THRESHOLD_HIGH", 20.0, float)
VIDEO_WAKE_THRESHOLD = _get_conf("VIDEO_WAKE_THRESHOLD", 5.0, float)
DOOM_SCROLL_THRESHOLD = _get_conf("DOOM_SCROLL_THRESHOLD", 3, int)

# Privacy
SENSITIVE_APP_KEYWORDS = _get_conf("SENSITIVE_APP_KEYWORDS", ["Keepass", "LastPass", "1Password", "Bitwarden", "Incognito", "InPrivate", "Tor Browser", "password", "vault", "private"])

# Video Polling Delays (Eco Mode)
VIDEO_ACTIVE_DELAY = _get_conf("VIDEO_ACTIVE_DELAY", 0.05, float) # 20 FPS
VIDEO_ECO_MODE_DELAY = _get_conf("VIDEO_ECO_MODE_DELAY", 0.2, float) # 5 FPS (Required for <200ms wake-up latency)

# --- Meeting Mode ---
MEETING_MODE_SPEECH_DURATION_THRESHOLD = _get_conf("MEETING_MODE_SPEECH_DURATION_THRESHOLD", 3.0, float)
MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = _get_conf("MEETING_MODE_IDLE_KEYBOARD_THRESHOLD", 10.0, float)
MEETING_MODE_SPEECH_GRACE_PERIOD = _get_conf("MEETING_MODE_SPEECH_GRACE_PERIOD", 2.0, float)

# --- VAD (Voice Activity Detection) ---
# RMS Threshold to consider "not silence"
VAD_SILENCE_THRESHOLD = _get_conf("VAD_SILENCE_THRESHOLD", 0.01, float)
VAD_WEAK_THRESHOLD = _get_conf("VAD_WEAK_THRESHOLD", 0.4, float)
VAD_STRONG_THRESHOLD = _get_conf("VAD_STRONG_THRESHOLD", 0.7, float)

# --- State Engine Baseline ---
# Allows personalization of the "neutral" state.
BASELINE_STATE = _get_conf("BASELINE_STATE", {
    "arousal": 50,
    "overload": 0,
    "focus": 50,
    "energy": 80,
    "mood": 50
}, dict)

# --- Video Sensor Baseline ---
# Personal calibration data for posture (tilt, position, etc.)
BASELINE_POSTURE = _get_conf("BASELINE_POSTURE", {}, dict)

# --- Intervention Engine ---
MIN_TIME_BETWEEN_INTERVENTIONS = _get_conf("MIN_TIME_BETWEEN_INTERVENTIONS", 300, int)
DEFAULT_INTERVENTION_DURATION = _get_conf("DEFAULT_INTERVENTION_DURATION", 30, int)

# --- LMM Configuration ---
# Note: API Keys should ideally be strictly ENV for security, but we allow config for local URLs.
LOCAL_LLM_URL = _get_conf("LOCAL_LLM_URL", "http://127.0.0.1:1234")
LOCAL_LLM_MODEL_ID = _get_conf("LOCAL_LLM_MODEL_ID", "deepseek/deepseek-r1-0528-qwen3-8b")

LMM_FALLBACK_ENABLED = _get_conf("LMM_FALLBACK_ENABLED", True, bool)
LMM_CIRCUIT_BREAKER_MAX_FAILURES = _get_conf("LMM_CIRCUIT_BREAKER_MAX_FAILURES", 5, int)
LMM_CIRCUIT_BREAKER_COOLDOWN = _get_conf("LMM_CIRCUIT_BREAKER_COOLDOWN", 60, int)

# --- API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Tiered Intervention Configurations ---
# (Used for legacy ad-hoc interventions or fallback defaults)
INTERVENTION_CONFIGS = {
    "gentle_reminder_text": {
        "tier": 1,
        "default_message": "This is a gentle reminder.",
        "default_duration": 10,
    },
    "posture_alert_text": {
        "tier": 1,
        "default_message": "Please check your posture.",
        "default_duration": 15,
    },
    "calming_audio_prompt": {
        "tier": 2,
        "default_message": "Let's try a calming sound.",
        "default_duration": 60,
        "sound_file": "sounds/calming_waves.wav",
    },
    "guided_breathing_prompt": {
        "tier": 2,
        "default_message": "Time for a short breathing exercise. Follow the prompts.",
        "default_duration": 120,
        "sound_file": "sounds/breathing_guide.mp3",
    },
    "urgent_break_alert": {
        "tier": 3,
        "default_message": "It's important to take a break now. Please step away for 5 minutes.",
        "default_duration": 300,
        "sound_file": "sounds/urgent_alert_tone.wav",
        "force_action": True,
    }
}
