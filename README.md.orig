# ASDGPT: Autonomous Co-Regulator

ASDGPT is a Python application designed to act as an autonomous co-regulator. It aims to monitor user activity through video and audio sensors and provide timely interventions or suggestions to help users manage their state, focus, and well-being.

## Features

*   **State Management**: Tracks user state (Active, Snoozed, Paused, DND).
*   **Sensor Input**: Captures data from camera (video) and microphone (audio).
*   **Intervention System**: Provides notifications and interventions (TTS, audio prompts).
*   **User Feedback**: Allows users to provide feedback on interventions via hotkeys.
*   **Hotkey Controls**: Easily manage application state and provide feedback without GUI interaction.
*   **System Tray Icon**: Provides a visual indicator of the application's status and quick access to controls.
*   **Data Logging**: Logs application events, errors, and sensor data for debugging and analysis.
*   **Context Intelligence**: Uses active window titles to infer user context (Work, Leisure, Doom Scrolling) and build a history narrative.
*   **Reflexive Triggers**: Instantly reacts to specific window titles (e.g., distraction apps) with pre-defined interventions.

## How it Works

ASDGPT operates as a continuous loop:
1.  **Senses**: Monitors audio (speech rate, tone) and video (posture, activity).
2.  **Analyzes**: Sends aggregated data to a local Large Multi-modal Model (LMM).
3.  **Updates State**: Tracks 5 internal dimensions (Arousal, Overload, Focus, Energy, Mood).
4.  **Intervenes**: Suggests micro-regulations (breathing, breaks) if state thresholds are crossed.
5.  **Learns**: You use hotkeys to mark interventions as "Helpful" or "Unhelpful", tuning future responses.

For a detailed breakdown of the internal architecture and data flow, see [Architecture & Data Flow](docs/ARCHITECTURE.md).

## Setup and Installation

### System Requirements

*   **OS**: Windows, Linux, or macOS.
*   **Python**: 3.8 or higher.
*   **Hardware**: Webcam and Microphone.

**Linux Users:**
For active window detection to work, you must have `xprop` installed (part of `x11-utils` on Debian/Ubuntu).
```bash
sudo apt-get install x11-utils
```
*Note: Window detection on Wayland is currently limited.*

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd ASDGPT
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    Ensure you have Python 3.8+ installed. Dependencies are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```
    *Note: `pystray` might have system-specific dependencies for the icon. `sounddevice` might require system audio libraries (e.g., PortAudio).*

## Configuration

ASDGPT can be configured via environment variables (for temporary overrides or secrets), a user config file (for persistent settings), or default values.

The priority order is:
1.  **Environment Variables** (Highest)
2.  `user_data/config.json`
3.  **Defaults** (Lowest)

### Key Environment Variables

Create a `.env` file in the project root to set these.
**Important:** Use `KEY=VALUE` syntax (no colons or spaces around the equals sign).

Example `.env` content:
```env
APP_NAME=MyCoRegulator
LOG_LEVEL=DEBUG
LOCAL_LLM_URL=http://localhost:1234/v1/chat/completions
```

**System & Logging**
*   `APP_NAME`: Name of the application (Default: "ACR")
*   `LOG_LEVEL`: Logging verbosity (Default: "INFO", options: DEBUG, INFO, WARNING, ERROR)
*   `USER_DATA_DIR`: Directory for storing user data (Default: "user_data")

**Sensors**
*   `CAMERA_INDEX`: Index of the camera to use (Default: 0)
*   `AUDIO_THRESHOLD_HIGH`: RMS threshold for high audio levels (Default: 0.5)
*   `VIDEO_ACTIVITY_THRESHOLD_HIGH`: Threshold for high video activity (Default: 20.0)
*   `VAD_SILENCE_THRESHOLD`: RMS threshold for silence (Default: 0.01)

**LMM Integration**
*   `LOCAL_LLM_URL`: URL for the local LLM server (Default: "http://127.0.0.1:1234")
*   `LOCAL_LLM_MODEL_ID`: Model ID for the local LLM (Default: "deepseek/deepseek-r1-0528-qwen3-8b")
*   `GOOGLE_API_KEY`: API key for Google services if needed (Optional)

**Hotkeys**
*   `HOTKEY_CYCLE_MODE`: Cycle modes (Default: "ctrl+alt+m")
*   `HOTKEY_PAUSE_RESUME`: Toggle pause (Default: "ctrl+alt+p")
*   `HOTKEY_FEEDBACK_HELPFUL`: Rate intervention helpful (Default: "ctrl+alt+up")
*   `HOTKEY_FEEDBACK_UNHELPFUL`: Rate intervention unhelpful (Default: "ctrl+alt+down")

**Meeting Mode**
*   `MEETING_MODE_SPEECH_DURATION_THRESHOLD`: Seconds of continuous speech to trigger (Default: 3.0)
*   `MEETING_MODE_IDLE_KEYBOARD_THRESHOLD`: Seconds of idle keyboard before allowing trigger (Default: 10.0)
*   `MEETING_MODE_SPEECH_GRACE_PERIOD`: Seconds allowed between words before speech is considered stopped (Default: 2.0)

**Resilience**
*   `LMM_FALLBACK_ENABLED`: Enable offline heuristics if LMM is unreachable (Default: True)
*   `LMM_CIRCUIT_BREAKER_MAX_FAILURES`: Failures before pausing LMM calls (Default: 5)

### User Config File

You can also create a `user_data/config.json` file to persist your settings:

```json
{
  "CAMERA_INDEX": 1,
  "SNOOZE_DURATION": 1800,
  "HOTKEY_CYCLE_MODE": "ctrl+shift+m"
}
```

## Calibration

ASDGPT includes a calibration wizard to personalize sensor thresholds for your environment. This is recommended for first-time setup.

To run the calibration tool:

```bash
python tools/calibrate.py
```

The wizard will guide you through:
1.  **Audio Silence Calibration**: Measures background noise to set `VAD_SILENCE_THRESHOLD`.
2.  **Video Posture Calibration**: Captures your neutral posture to set `BASELINE_POSTURE` for accurate posture correction.

Settings are saved to `user_data/config.json`.

## Running the Application

Execute the `main.py` script from the project root:

```bash
python main.py
```

The application will start, and a system tray icon should appear.

## Modes of Operation

*   **Active**: The application is actively monitoring sensor data and may provide interventions.
*   **Snoozed**: Interventions are suppressed for a set duration (`SNOOZE_DURATION`). Returns to "Active" automatically.
*   **DND (Do Not Disturb)**: Monitoring continues, but all interventions are suppressed indefinitely.
*   **Meeting Mode (Auto-DND)**: Automatically switches to **DND** when continuous speech is detected along with a face, and the keyboard is idle. This prevents interventions during calls.
    *   *Triggers*: Speech > 3s + Face Detected + Keyboard Idle > 10s.
    *   *Exits*: Automatically exits to **Active** when user input (keyboard/mouse) is detected.
*   **Paused**: All active monitoring and interventions are stopped.

## Contributing

Details for contributing will be added later. For now, focus on understanding the existing structure and planned LMM integration.

## How to Verify

### Meeting Mode (Auto-DND)
To verify that the system correctly identifies meetings and suppresses interventions:

1.  **Ensure you are in 'Active' mode.**
2.  **Stop typing/using the mouse** for at least 10 seconds.
3.  **Speak continuously** for 3-5 seconds while looking at the camera.
4.  **Observe**: The system tray icon (or logs) should indicate a switch to `DND` mode.
5.  **Touch the keyboard**: The mode should immediately switch back to `Active`.

## Testing

Run the test suite using `pytest` or `make`:

```bash
make test
```

We also provide a **Replay Harness** for deterministic testing of Logic Engine scenarios:

```bash
make replay
```

### Maintenance

To clean up temporary files (logs, captures, caches):

```bash
make clean
```

### Stress Testing

To verify system reliability and clean shutdown behavior:

```bash
python tools/verify_crash.py
```

## Documentation

*   **[Architecture & Data Flow](docs/ARCHITECTURE.md)**: Technical overview of components and data flow.
*   **[Mental Model & Design Specification](docs/MENTAL_MODEL.md)**: The core philosophy and design spec.
*   **[Project Specification](docs/PROJECT_SPECIFICATION.md)**: Detailed Master Specification (v4).
