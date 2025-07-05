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

# (Future task 4.5 - API Keys - will be loaded from .env)
# GOOGLE_API_KEY = "YOUR_API_KEY_HERE" # Example, actual key loaded from .env

# Logging configuration (can be expanded)
LOG_LEVEL = "INFO" # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "acr_app.log" # Changed from acr_log.txt for consistency with main.py

# Sensor configurations (can be expanded)
CAMERA_INDEX = 0 # Default camera index
# AUDIO_DEVICE_INDEX = None # Example: Or specific index

# STT Configuration
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15" # Default path, user should verify or change
                                                # Download models from https://alphacephei.com/vosk/models
                                                # Place it in the root directory or provide full path.

# TTS Configuration
ENABLE_TTS_OUTPUT = True  # Master switch for TTS voice output
TTS_VOICE_ID = None       # Set to a specific voice ID string from available system voices.
                          # Example: "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_ZIRA_11.0" (Windows)
                          # Example: "com.apple.speech.synthesis.voice.daniel" (macOS)
                          # Leave as None to use the system default voice.
                          # The available voice IDs will be logged by InterventionEngine on startup if INFO logging is enabled.
TTS_VOICE_ID = None       # Set to a specific voice ID string from available system voices.
ENABLE_TTS_OUTPUT = True  # Master switch for TTS voice output
TTS_RATE = 150            # Speech rate. Default is often 200. Lower is slower.

# STT Configuration
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15" # Default path, user should verify or change
                                                # Download models from https://alphacephei.com/vosk/models
                                                # Place it in the root directory or provide full path.

# Intervention Engine settings
MIN_TIME_BETWEEN_INTERVENTIONS = 300 # seconds, e.g., 5 minutes (for proactive, non-mode-change interventions)

# System Tray settings
APP_NAME = "ACR"
