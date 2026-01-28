# AC-CoRegulator (Project Sentinel/Navigator)

**Project Code:** `ACR`
**Version:** 0.5.0 (Navigator Phase)
**Status:** In Development (See `ROADMAP.md` for current sprint)

## Overview

AC-CoRegulator is an AI-powered desktop application designed to act as a "Co-Regulator" for the user. It monitors physiological and behavioral cues (via webcam and microphone) to estimate the user's state (Focus, Arousal, Overload) and intervenes in real-time to prevent burnout or panic attacks.

It uses a local **Large Multimodal Model (LMM)** (running via LM Studio or similar) to analyze sensor data while preserving privacy.

## Key Features (Implemented)

*   **Privacy-First:** All data processing (video/audio) happens locally. No cloud uploads.
*   **Sensor Fusion:** Combines audio prosody (volume, pitch) and video analysis (movement, face detection).
*   **State Estimation:** Real-time estimation of Arousal and Overload levels.
*   **Intervention Engine:** Delivers audio or visual feedback (e.g., "Breathe", "Take a break") based on state.
*   **System Tray Integration:** Status icon and control menu.
*   **Resilience:**
    *   **Circuit Breaker:** Handles LMM timeouts/failures gracefully.
    *   **Offline Fallback:** Switches to rule-based logic if LMM is unavailable.
    *   **Self-Healing:** Automatic recovery from sensor errors.
*   **Personalization:**
    *   **Calibration Wizard:** Interactive tool to baseline silence and posture.

## Prerequisities

1.  **Python 3.10+**
2.  **LM Studio** (or equivalent local LLM server) running an OpenAI-compatible server on port `1234`.
    *   Recommended Model: `Llama 3.2 3B Instruct` or `Phi-3.5 Vision`.
3.  **Webcam & Microphone**

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repo_url>
    cd <repo_name>
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Copy `config.py` (defaults) or create a `.env` file to override settings.

## Usage

1.  **Start Local LLM:**
    Launch LM Studio, load a vision-capable model, and start the server (ensure "Cross-Origin Resource Sharing (CORS)" is enabled if needed, though Python requests don't strictly require it).

2.  **Calibrate (Optional but Recommended):**
    Run the calibration tool to set your baseline.
    ```bash
    python tools/calibrate.py
    ```
    Follow the on-screen instructions.

3.  **Run the App:**
    ```bash
    python main.py
    ```

4.  **System Tray:**
    *   **Right-Click:** Open menu (Status, Calibration, Settings, Exit).
    *   **Icon Color:**
        *   Green: Active & Good State
        *   Yellow: Moderate Arousal/Warning
        *   Red: High Arousal/Intervention
        *   Grey: Snoozed/Inactive

## Configuration (`config.py` / `.env`)

The application is configurable via `config.py`. You can override defaults using environment variables.

The priority order is:
1.  Environment Variables (`.env`)
2.  `config.py` Defaults

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
*   `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
*   `LOG_FILE`: Path to log file.

**LMM Settings**
*   `LOCAL_LLM_URL`: URL of the local LLM server (Default: `http://localhost:1234/v1/chat/completions`)
*   `LOCAL_LLM_MODEL_ID`: Model identifier string (Default: `local-model`)

**Sensor Settings**
*   `CAMERA_INDEX`: ID of the webcam to use (Default: 0)
*   `AUDIO_SAMPLE_RATE`: Audio sample rate (Default: 16000)

## Development

*   **Tests:** Run unit tests with `pytest`.
    ```bash
    pytest
    ```
*   **Linting:** Follow PEP 8 standards.

## Contributing

See `ROADMAP.md` for current tasks and priorities.
Please use a feature branch for all changes and submit a Pull Request.

## License

[License Name]
