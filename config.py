# Configuration for the Autonomous Co-Regulator
import os
from dotenv import load_dotenv

load_dotenv()

load_dotenv()

# --- Application Mode ---
# Default mode for the application
# Options: "active", "snoozed", "paused"
DEFAULT_MODE = "active"

# Snooze duration in seconds (e.g., 1 hour = 3600 seconds)
SNOOZE_DURATION = 3600

# --- Hotkeys ---
# Note: Ensure these are not commonly used system-wide hotkeys
HOTKEY_CYCLE_MODE = "ctrl+alt+m"  # Cycle through active, snoozed, paused
HOTKEY_PAUSE_RESUME = "ctrl+alt+p" # Toggle between paused and previously active/snoozed state
HOTKEY_FEEDBACK_HELPFUL = "ctrl+alt+up"
HOTKEY_FEEDBACK_UNHELPFUL = "ctrl+alt+down"

# --- User Feedback ---
FEEDBACK_WINDOW_SECONDS = 15 # Time in seconds to provide feedback after an intervention
FEEDBACK_SUPPRESSION_MINUTES = 240 # Suppress "unhelpful" interventions for 4 hours

# --- System & Logging ---
APP_NAME = "ACR"
LOG_LEVEL = "INFO" # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "acr_app.log"
USER_DATA_DIR = "user_data"
SUPPRESSIONS_FILE = os.path.join(USER_DATA_DIR, "suppressions.json")
PREFERENCES_FILE = os.path.join(USER_DATA_DIR, "preferences.json")
EVENTS_FILE = os.path.join(USER_DATA_DIR, "events.jsonl")

# --- API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Sensors ---
CAMERA_INDEX = 0
# Thresholds
AUDIO_THRESHOLD_HIGH = float(os.getenv("AUDIO_THRESHOLD_HIGH", 0.3)) # RMS level to trigger "loud" event (0.0 - 1.0)
VIDEO_ACTIVITY_THRESHOLD_HIGH = float(os.getenv("VIDEO_ACTIVITY_THRESHOLD_HIGH", 20.0)) # Frame diff score to trigger "active" event

# --- Intervention Engine ---
MIN_TIME_BETWEEN_INTERVENTIONS = 300 # seconds (5 minutes)
DEFAULT_INTERVENTION_DURATION = 30 # seconds
# (Future task 4.5 - API Keys - will be loaded from .env)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Sensor Thresholds (Calibrated via tools/calibrate_sensors.py)
# Defaults are conservative if not set in .env
AUDIO_THRESHOLD_HIGH = float(os.getenv("AUDIO_THRESHOLD_HIGH", "0.5"))
VIDEO_ACTIVITY_THRESHOLD_HIGH = float(os.getenv("VIDEO_ACTIVITY_THRESHOLD_HIGH", "20.0"))
DOOM_SCROLL_THRESHOLD = int(os.getenv("DOOM_SCROLL_THRESHOLD", "3"))

# Logging configuration (can be expanded)
LOG_LEVEL = "INFO" # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "acr_app.log" # Changed from acr_log.txt for consistency with main.py

# --- LMM Configuration ---
LOCAL_LLM_URL = "http://127.0.0.1:1234"
LOCAL_LLM_MODEL_ID = "deepseek/deepseek-r1-0528-qwen3-8b"

# Reliability Settings
LMM_FALLBACK_ENABLED = True
LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
LMM_CIRCUIT_BREAKER_COOLDOWN = 60 # seconds
# Thresholds (Overridable by environment variables for personalization)
AUDIO_THRESHOLD_HIGH = float(os.getenv("AUDIO_THRESHOLD_HIGH", "0.5"))
VIDEO_ACTIVITY_THRESHOLD_HIGH = float(os.getenv("VIDEO_ACTIVITY_THRESHOLD_HIGH", "20.0"))

# Intervention Engine settings
MIN_TIME_BETWEEN_INTERVENTIONS = 300 # seconds, e.g., 5 minutes (for proactive, non-mode-change interventions)
DEFAULT_INTERVENTION_DURATION = 30 # Default duration for an intervention if not specified (seconds)

# --- Tiered Intervention Configurations ---
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


# System Tray settings
APP_NAME = "ACR"

# LMM Configuration
LOCAL_LLM_URL = "http://127.0.0.1:1234"
LOCAL_LLM_MODEL_ID = "deepseek/deepseek-r1-0528-qwen3-8b"
LMM_FALLBACK_ENABLED = True # Return neutral state if LMM is unreachable
LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
LMM_CIRCUIT_BREAKER_COOLDOWN = 60 # seconds

USER_DATA_DIR = "user_data"
SUPPRESSIONS_FILE = os.path.join(USER_DATA_DIR, "suppressions.json")
PREFERENCES_FILE = os.path.join(USER_DATA_DIR, "preferences.json")

# LMM Reliability Settings
LMM_FALLBACK_ENABLED = True
LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
LMM_CIRCUIT_BREAKER_COOLDOWN = 60 # seconds
EVENTS_FILE = os.path.join(USER_DATA_DIR, "events.jsonl")
