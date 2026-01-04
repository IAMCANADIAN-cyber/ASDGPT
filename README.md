# ASDGPT: Autonomous Co-Regulator

ASDGPT is a Python application designed to act as an autonomous co-regulator. It monitors user activity through video and audio sensors and provides timely interventions or suggestions to help users manage their state, focus, and well-being. The project uses a local Large Language Model (LMM) for intelligent data processing and decision-making.

## Features

*   **State Management**: Tracks user state (Active, Snoozed, Paused) and estimates internal state (Arousal, Overload, Focus, Energy, Mood).
*   **Sensor Input**: Captures data from camera (video) and microphone (audio) to analyze activity levels, posture, and ambient noise.
*   **Local LMM Integration**: Connects to a local OpenAI-compatible endpoint (e.g., LM Studio) to analyze context and suggest interventions privately.
*   **Intervention System**: Delivers tiered interventions (TTS, audio prompts, visual alerts) based on state estimation.
*   **User Feedback**: Allows users to rate interventions as "Helpful" or "Unhelpful" via hotkeys, refining future suggestions.
*   **System Tray Icon**: Provides a visual indicator of status (Active/Snoozed/Error) and quick access to controls.
*   **Data Logging**: Logs structured events, errors, and sensor metrics for debugging and timeline generation.

## Setup and Installation

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
    *Note: `sounddevice` requires system audio libraries (e.g., `portaudio19-dev` on Linux).*
    *Note: `keyboard` requires root/sudo privileges on Linux to intercept global hotkeys.*

4.  **Local LMM Setup:**
    This project requires a local LLM server compatible with the OpenAI API format (e.g., LM Studio, Ollama, LocalAI).
    *   **Recommended**: [LM Studio](https://lmstudio.ai/)
    *   **Model**: A vision-capable model is recommended but not strictly required if only text context is used.
    *   **Server**: Start the server on `http://127.0.0.1:1234` (default).

5.  **Environment Variables:**
    Create a `.env` file in the project root to override defaults.
    ```env
    # LMM Configuration
    LOCAL_LLM_URL="http://127.0.0.1:1234/v1/chat/completions"
    LOCAL_LLM_MODEL_ID="deepseek/deepseek-r1-0528-qwen3-8b"

    # Sensor Thresholds
    AUDIO_THRESHOLD_HIGH=0.5
    VIDEO_ACTIVITY_THRESHOLD_HIGH=20.0
    ```

## Running the Application

Execute the `main.py` script from the project root. On Linux, you may need `sudo` for global hotkeys:

```bash
# Windows / Mac
python main.py

# Linux (for global hotkeys)
sudo ./venv/bin/python main.py
```

The application will start, and a system tray icon should appear.

## Hotkeys

The following hotkeys are configured by default (see `config.py` to customize):

*   **`Ctrl+Alt+M`**: Cycle through modes (Active -> Snoozed -> Paused -> Active).
*   **`Ctrl+Alt+P`**: Toggle Pause/Resume. If paused, restores the previous state.
*   **`Ctrl+Alt+Up`**: Register "Helpful" feedback for the last intervention.
*   **`Ctrl+Alt+Down`**: Register "Unhelpful" feedback for the last intervention.
*   **`Esc`**: Quit the application.

## Modes of Operation

*   **Active**: The application monitors sensor data. If activity thresholds are crossed, it sends a snapshot to the LMM for state estimation and potential intervention.
*   **Snoozed**: Interventions are suppressed for a set duration (default 1 hour). State monitoring continues in the background.
*   **Paused**: All monitoring and interventions are stopped.
*   **Error**: Indicates a sensor failure. The tray icon will change to reflect this.

## Project Structure

*   `main.py`: Entry point and orchestrator.
*   `config.py`: Configuration settings and environment variable loading.
*   `core/`:
    *   `logic_engine.py`: Core loop, threshold checks, and state machine.
    *   `lmm_interface.py`: Handles communication with the local LLM.
    *   `intervention_engine.py`: Manages intervention execution and feedback.
*   `sensors/`:
    *   `video_sensor.py`: Webcam capture and basic frame analysis.
    *   `audio_sensor.py`: Microphone capture and RMS/Pitch analysis.
*   `user_data/`: Stores local logs, preferences, and suppression data (ignored by git).

## Contributing

Please refer to `AGENTS.md` for coding guidelines and `ROADMAP.md` for planned features.

## Testing

Run the test suite using `pytest`:

```bash
pytest
```

## Design & Mental Model

*   [Mental Model & Design Specification](docs/MENTAL_MODEL.md): Deep dive into the 5D state estimation and intervention philosophy.
*   [Project Specification](docs/PROJECT_SPECIFICATION.md): Detailed Master Specification (v4) for the "Guardian Angel" architecture.
