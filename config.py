# Configuration for the Autonomous Co-Regulator
import os
import json
from dotenv import load_dotenv

load_dotenv()

# --- System & Logging ---
APP_NAME = "ACR"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO") # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "acr_app.log"
USER_DATA_DIR = "user_data"
SUPPRESSIONS_FILE = os.path.join(USER_DATA_DIR, "suppressions.json")
PREFERENCES_FILE = os.path.join(USER_DATA_DIR, "preferences.json")
EVENTS_FILE = os.path.join(USER_DATA_DIR, "events.jsonl")
CALIBRATION_FILE = os.path.join(USER_DATA_DIR, "calibration.json")

# --- Application Mode ---
DEFAULT_MODE = "active"
SNOOZE_DURATION = 3600

# --- Hotkeys ---
HOTKEY_CYCLE_MODE = "ctrl+alt+m"
HOTKEY_PAUSE_RESUME = "ctrl+alt+p"
HOTKEY_FEEDBACK_HELPFUL = "ctrl+alt+up"
HOTKEY_FEEDBACK_UNHELPFUL = "ctrl+alt+down"

# --- User Feedback ---
FEEDBACK_WINDOW_SECONDS = 15
FEEDBACK_SUPPRESSION_MINUTES = 240

# --- Sensors & Thresholds ---
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))

# Default Thresholds (Environment Variables override code defaults)
_audio_thresh_default = float(os.getenv("AUDIO_THRESHOLD_HIGH", 0.5))
_video_thresh_default = float(os.getenv("VIDEO_ACTIVITY_THRESHOLD_HIGH", 20.0))
DOOM_SCROLL_THRESHOLD = int(os.getenv("DOOM_SCROLL_THRESHOLD", "3"))

# Load Calibration Override if available
if os.path.exists(CALIBRATION_FILE):
    try:
        with open(CALIBRATION_FILE, 'r') as f:
            _cal_data = json.load(f)
            # Only override if keys exist and are valid numbers
            if "audio_threshold_high" in _cal_data:
                _audio_thresh_default = float(_cal_data["audio_threshold_high"])
            if "video_activity_threshold_high" in _cal_data:
                _video_thresh_default = float(_cal_data["video_activity_threshold_high"])
            # print(f"Loaded calibration data: {_cal_data}")
    except Exception as e:
        print(f"Warning: Failed to load calibration file: {e}")

AUDIO_THRESHOLD_HIGH = _audio_thresh_default
VIDEO_ACTIVITY_THRESHOLD_HIGH = _video_thresh_default

# --- API Keys ---
# (Loaded from .env if available)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Sensors ---
CAMERA_INDEX = 0

# Thresholds (Calibrated via tools/calibrate_sensors.py or .env)
# Defaults are conservative if not set in .env
AUDIO_THRESHOLD_HIGH = float(os.getenv("AUDIO_THRESHOLD_HIGH", "0.5"))
VIDEO_ACTIVITY_THRESHOLD_HIGH = float(os.getenv("VIDEO_ACTIVITY_THRESHOLD_HIGH", "20.0"))
DOOM_SCROLL_THRESHOLD = int(os.getenv("DOOM_SCROLL_THRESHOLD", "3"))

# --- Intervention Engine ---
MIN_TIME_BETWEEN_INTERVENTIONS = 300 # seconds (5 minutes)
DEFAULT_INTERVENTION_DURATION = 30 # seconds

# --- LMM Configuration ---
LOCAL_LLM_URL = "http://127.0.0.1:1234"
LOCAL_LLM_MODEL_ID = "deepseek/deepseek-r1-0528-qwen3-8b"
LMM_FALLBACK_ENABLED = True
LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
LMM_CIRCUIT_BREAKER_COOLDOWN = 60

# --- Intervention Engine ---
MIN_TIME_BETWEEN_INTERVENTIONS = 300
DEFAULT_INTERVENTION_DURATION = 30
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Tiered Intervention Configurations (Legacy/Fallback) ---
LMM_CIRCUIT_BREAKER_COOLDOWN = 60 # seconds

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
