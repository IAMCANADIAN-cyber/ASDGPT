# Configuration for the Autonomous Co-Regulator

# Default mode for the application
# Options: "active", "snoozed", "paused"
DEFAULT_MODE = "active"

# Snooze duration in seconds (e.g., 1 hour = 3600 seconds)
SNOOZE_DURATION = 3600  # 1 hour

# Hotkeys
# Note: Ensure these are not commonly used system-wide hotkeys
HOTKEY_CYCLE_MODE = "ctrl+alt+m"  # Cycle through active, snoozed, paused
HOTKEY_PAUSE_RESUME = "ctrl+alt+p" # Toggle between paused and previously active/snoozed state

# User Feedback Hotkeys (Task 4.4)
HOTKEY_FEEDBACK_HELPFUL = "ctrl+alt+up"
HOTKEY_FEEDBACK_UNHELPFUL = "ctrl+alt+down"
FEEDBACK_WINDOW_SECONDS = 15 # Time in seconds to provide feedback after an intervention
FEEDBACK_SUPPRESSION_MINUTES = 240 # Suppress "unhelpful" interventions for 4 hours

import os
from dotenv import load_dotenv

load_dotenv()

# (Future task 4.5 - API Keys - will be loaded from .env)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Logging configuration (can be expanded)
LOG_LEVEL = "INFO" # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "acr_app.log" # Changed from acr_log.txt for consistency with main.py

# Sensor configurations (can be expanded)
CAMERA_INDEX = 0 # Default camera index
# AUDIO_DEVICE_INDEX = None # Example: Or specific index

# Intervention Engine settings
MIN_TIME_BETWEEN_INTERVENTIONS = 300 # seconds, e.g., 5 minutes (for proactive, non-mode-change interventions)
DEFAULT_INTERVENTION_DURATION = 30 # Default duration for an intervention if not specified (seconds)

# Tiered Intervention Configurations
# This allows defining default properties for different types/tiers of interventions.
# LogicEngine can then select an intervention and pass its details to InterventionEngine.
INTERVENTION_CONFIGS = {
    "gentle_reminder_text": {
        "tier": 1,
        "default_message": "This is a gentle reminder.",
        "default_duration": 10, # seconds
        # "sound": None, # No sound for tier 1 text
    },
    "posture_alert_text": {
        "tier": 1,
        "default_message": "Please check your posture.",
        "default_duration": 15,
    },
    "calming_audio_prompt": {
        "tier": 2,
        "default_message": "Let's try a calming sound.",
        "default_duration": 60, # Duration of the audio or overall intervention
        "sound_file": "sounds/calming_waves.wav", # Example path
        "visual_prompt": None, # Could be an image path or text for a pop-up
    },
    "guided_breathing_prompt": {
        "tier": 2,
        "default_message": "Time for a short breathing exercise. Follow the prompts.",
        "default_duration": 120,
        "sound_file": "sounds/breathing_guide.mp3",
        "visual_prompt": "images/breathing_animation.gif", # Example
    },
    "urgent_break_alert": {
        "tier": 3,
        "default_message": "It's important to take a break now. Please step away for 5 minutes.",
        "default_duration": 300, # Enforces a 5-min period where the alert might be active/repeating
        "sound_file": "sounds/urgent_alert_tone.wav",
        "visual_prompt": "TAKE A BREAK NOW - 5 MINUTES", # Text for a more prominent visual
        "force_action": True, # Custom flag, could indicate LogicEngine should try to e.g. overlay screen
    }
    # Add more predefined interventions as needed
}


# System Tray settings
APP_NAME = "ACR"

# LMM Configuration
LOCAL_LLM_URL = "http://127.0.0.1:1234"
LOCAL_LLM_MODEL_ID = "deepseek/deepseek-r1-0528-qwen3-8b"
LMM_FALLBACK_ENABLED = True # Return neutral state if LMM is unreachable
LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
LMM_CIRCUIT_BREAKER_COOLDOWN = 60 # seconds
LMM_FALLBACK_ENABLED = True # Return neutral state if LMM is offline

USER_DATA_DIR = "user_data"
SUPPRESSIONS_FILE = os.path.join(USER_DATA_DIR, "suppressions.json")

# LMM Reliability Settings
LMM_FALLBACK_ENABLED = True
LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
LMM_CIRCUIT_BREAKER_COOLDOWN = 60 # seconds
EVENTS_FILE = os.path.join(USER_DATA_DIR, "events.jsonl")
