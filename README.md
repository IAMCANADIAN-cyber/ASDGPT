# ASDGPT: Autonomous Co-Regulator

ASDGPT is a Python application designed to act as an autonomous co-regulator. It aims to monitor user activity through video and audio sensors and provide timely interventions or suggestions to help users manage their state, focus, and well-being. The project is intended to leverage Large Language Models (LMMs) for intelligent data processing and decision-making, though current LMM integration is at a placeholder stage.

## Features

*   **State Management**: Tracks user state (active, snoozed, paused).
*   **Sensor Input**: Captures data from camera (video) and microphone (audio). (Requires appropriate hardware and permissions).
*   **Intervention System**: Can provide notifications and interventions (currently placeholder TTS).
*   **User Feedback**: Allows users to provide feedback on interventions via hotkeys.
*   **Hotkey Controls**: Easily manage application state and provide feedback without GUI interaction.
*   **System Tray Icon**: Provides a visual indicator of the application's status and quick access to controls.
*   **Data Logging**: Logs application events, errors, and sensor data for debugging and analysis.

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
    *Note: `pystray` might have system-specific dependencies for the icon. `sounddevice` might require system audio libraries (e.g., PortAudio).*

4.  **Environment Variables (for LMM Integration):**
    If you intend to use actual LMM capabilities (once fully implemented), you'll need to set up API keys.
    *   Create a file named `.env` in the project root directory.
    *   Add your API keys to this file, for example:
        ```env
        GOOGLE_API_KEY="YOUR_ACTUAL_GOOGLE_API_KEY"
        ```
    *   The `core/lmm_interface.py` currently looks for `GOOGLE_API_KEY`.

## Running the Application

Execute the `main.py` script from the project root:

```bash
python main.py
```

The application will start, and a system tray icon should appear.

## Hotkeys

The following hotkeys are configured by default (see `config.py` to customize):

*   **`Ctrl+Alt+M`**: Cycle through modes (Active -> Snoozed -> Paused -> Active).
*   **`Ctrl+Alt+P`**: Toggle Pause/Resume. If paused, restores the previous state (Active or Snoozed). If active or snoozed, pauses the application.
*   **`Ctrl+Alt+Up`**: Register "Helpful" feedback for the last intervention.
*   **`Ctrl+Alt+Down`**: Register "Unhelpful" feedback for the last intervention.
*   **`Esc`**: Quit the application.

## Modes of Operation

*   **Active**: The application is actively monitoring sensor data and may provide interventions based on its logic and LMM suggestions.
*   **Snoozed**: Interventions are temporarily suppressed for a configured duration (e.g., 1 hour). The application will automatically return to "Active" mode when the snooze period ends. Sensor activity might still be monitored lightly or paused depending on implementation.
*   **Paused**: All active monitoring and interventions are stopped. The application remains in this state until manually resumed or cycled.
*   **Error**: If a critical sensor (or other component) error occurs, the application may enter an error state, indicated by the tray icon. Some functionalities might be limited.

## Project Structure

*   `main.py`: Main application entry point and orchestrator.
*   `config.py`: Application configuration settings.
*   `requirements.txt`: Python dependencies.
*   `core/`: Core logic modules.
    *   `logic_engine.py`: Manages application state.
    *   `intervention_engine.py`: Handles intervention delivery and feedback.
    *   `data_logger.py`: Logs application data.
    *   `system_tray.py`: Manages the system tray icon.
    *   `lmm_interface.py`: Placeholder for LMM interaction.
*   `sensors/`: Sensor data acquisition modules.
    *   `video_sensor.py`: Video capture.
    *   `audio_sensor.py`: Audio capture.
*   `assets/`: Icons and other static assets.
*   `AGENTS.md`: Instructions and guidelines for AI agents working on this codebase (to be created).

## Contributing

Details for contributing will be added later. For now, focus on understanding the existing structure and planned LMM integration.

## Future Development

*   Full LMM integration for intelligent analysis and intervention suggestions.
*   Advanced sensor data processing.
*   User-configurable intervention rules and preferences.
*   Expanded GUI for settings and data visualization.

## Testing

Run the test suite using `pytest`:

```bash
pytest
```

### Stress Testing

To verify system reliability and clean shutdown behavior (e.g., preventing zombie threads), run the crash stress test:

```bash
python tools/verify_crash.py
```

## Design & Mental Model

For a deep dive into the system's core philosophy, state definitions, and intervention strategies, please refer to the [Mental Model & Design Specification](docs/MENTAL_MODEL.md). This document serves as the engineering spec for the system's logic, covering:

*   **Mental Model**: 4 layers from sensors to learning.
*   **Signals & Checks**: Specific audio/video features to monitor.
*   **States**: 5D state estimation (Arousal, Overload, Focus, Energy, Mood).
*   **Interventions**: Structured intervention library and policy.
*   **Personalization**: How the system adapts to the user.

## Project Specification (Guardian Angel & Creative Director)

For the detailed Master Specification (v4) outlining the "Guardian Angel" and "Creative Director" architecture, including the local tech stack, functional modules, and specific intervention protocols, please refer to the [Project Specification](docs/PROJECT_SPECIFICATION.md).

---

*This README provides a basic overview. Further details on specific components can be found in their respective source files.*
