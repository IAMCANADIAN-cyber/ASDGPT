# ASDGPT: Autonomous Co-Regulator

ASDGPT is a Python application designed to act as an autonomous co-regulator. It monitors user activity through video and audio sensors and provides timely interventions or suggestions to help users manage their state, focus, and well-being.

## New Features (v2)

*   **Sexual Arousal & Content Creation Mode**: Dedicated support for tracking arousal states, suggesting poses, and managing "erotic content creation" workflows (auto-capture, digital PTZ).
*   **Voice Interaction**: Talk to the system using Speech-to-Text (STT) and receive verbal responses via Text-to-Speech (TTS). Supports local processing (Whisper) and voice cloning (Coqui TTS).
*   **Digital PTZ**: Automatically crops captured images to center on the subject, simulating a Pan-Tilt-Zoom camera.
*   **Social Media Integration**: Automatically drafts posts with AI-generated captions based on captured content.
*   **Music Control**: Changes music playlists based on your detected mood and arousal levels (supports Spotify).
*   **Configuration GUI**: A visual tool to easily manage settings.

## Setup and Installation

### System Requirements

*   **OS**: Windows, Linux, or macOS.
*   **Python**: 3.9 - 3.11 (Required for `TTS` package compatibility).
*   **Hardware**: Webcam and Microphone.
*   **System Libraries**:
    *   **Linux**: `x11-utils` (for window detection), `espeak` (TTS), `ffmpeg` (Audio), `portaudio19-dev` (Audio).
    *   **macOS**: `ffmpeg`, `portaudio`.
    *   **Windows**: Visual C++ Build Tools (often needed for audio libraries).

**Linux Dependencies Command:**
```bash
sudo apt-get install x11-utils espeak ffmpeg portaudio19-dev
```

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd ASDGPT
    ```

2.  **Create a virtual environment (Crucial):**
    ```bash
    python3.10 -m venv venv  # Python 3.10 recommended for ML compatibility
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    This installs all core libraries including PyTorch, Whisper, and SpeechRecognition.
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Installing `openai-whisper` and `TTS` (Coqui) may download significant model data.*

4.  **Install Optional Dependencies (Voice Cloning):**
    If you want advanced voice cloning, ensure `TTS` is installed correctly. It is **not** included in `requirements.txt` by default due to size and compatibility constraints.
    ```bash
    pip install TTS
    ```
    *Note: Requires Python < 3.12.*

## Configuration

For a comprehensive guide on all available settings, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

You can configure ASDGPT using the new Graphical Interface or by editing config files manually.

### Using the GUI (Recommended)

Run the configuration tool:
```bash
python tools/config_gui.py
```
This allows you to set:
*   **Thresholds**: Audio, Video, and Sexual Arousal sensitivity.
*   **Paths**: Where to save Erotic Content (`captures/erotic`).
*   **Voice**: Choose between 'system' (default) or 'coqui' (cloning) engines.
*   **Performance**: Toggle 'High' or 'Low' resource usage.

### Manual Configuration

You can override defaults by creating `user_data/config.json`. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the full list of options.

Example `user_data/config.json`:
```json
{
  "EROTIC_CONTENT_OUTPUT_DIR": "my_private_folder/captures",
  "SEXUAL_AROUSAL_THRESHOLD": 60,
  "TTS_ENGINE": "coqui",
  "TTS_VOICE_CLONE_SOURCE": "assets/my_voice.wav",
  "VOICE_COMMANDS": {
      "take a picture": "erotic_auto_capture",
      "how do i look": "erotic_pose_suggestion"
  },
  "PERFORMANCE_MODE": "high"
}
```

### Music Integration (Spotify)

To enable music control:
1.  Ensure you have a way to handle `spotify:` URIs (official Spotify app installed).
2.  On Linux, install `spotify-client`.
3.  The system currently uses system commands (`open`, `start`, `spotify`) to trigger playlists.

### Social Media Integration

Drafts are automatically saved to `drafts/instagram/` (or other platforms) when an erotic capture occurs.
*   Each draft includes the image and a JSON file with a generated caption.
*   **Note**: This feature creates *local drafts* only; it does not post to the internet automatically.

## Usage

1.  **Start the Application:**
    ```bash
    python main.py
    ```

2.  **Voice Commands:**
    Speak clearly into the microphone. Supported commands (customizable in config):
    *   "Take a picture" -> Captures image immediately.
    *   "Record this" -> Starts video recording.
    *   "Suggest a pose" -> System verbally suggests a pose.

3.  **Sexual Arousal Mode:**
    The system infers this state based on context (Late night + Low Light + Nudity/Pose + High Mood) or if manually triggered via voice.
    *   **Behavior**: Monitoring frequency increases. Interventions shift to encouragement and content capture.

## Troubleshooting

*   **"PortAudio not found" / "No module named sounddevice":**
    *   Install system audio libraries (see System Requirements).
*   **"TTS not found" / Import Errors:**
    *   Ensure you are using Python 3.9-3.11. Python 3.12+ has compatibility issues with the `TTS` library.
    *   If using `system` TTS, ensure `espeak` is installed (Linux).
*   **Xlib / Display Errors (Linux):**
    *   If running headless (no monitor), `pyautogui` features like media keys will fail. Run with a display or use `xvfb`.

## Testing

Run unit tests to verify installation:
```bash
python -m pytest tests/
```
