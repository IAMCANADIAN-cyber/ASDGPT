# ASDGPT: Autonomous Co-Regulator

ASDGPT is a Python application designed to act as an autonomous co-regulator. It monitors user activity through video and audio sensors and provides timely interventions or suggestions to help users manage their state, focus, and well-being.

## New Features (v2)

*   **Sexual Arousal & Content Creation Mode**: Dedicated support for tracking arousal states, suggesting poses, and managing "erotic content creation" workflows (auto-capture, digital PTZ).
*   **Voice Interaction**: Talk to the system using Speech-to-Text (STT) and receive verbal responses via Text-to-Speech (TTS). Supports local processing (Whisper) and voice cloning (Coqui TTS).
*   **Digital PTZ**: Automatically crops captured images to center on the subject, simulating a Pan-Tilt-Zoom camera.
*   **Social Media Integration**: Automatically drafts posts with AI-generated captions based on captured content.
*   **Music Control**: Changes music playlists based on your detected mood and arousal levels (supports Spotify).
*   **Configuration GUI**: A visual tool to easily manage settings.

## Core Features (v1)

*   **State Management**: Tracks user state (Active, Snoozed, Paused, DND).
*   **Sensor Input**: Captures data from camera (video) and microphone (audio).
*   **Intervention System**: Provides notifications and interventions (TTS, audio prompts).
*   **User Feedback**: Allows users to provide feedback on interventions via hotkeys.
*   **System Tray Icon**: Provides a visual indicator of the application's status and quick access to controls.
*   **Context Intelligence**: Uses active window titles to infer user context (Work, Leisure, Doom Scrolling).
*   **Reflexive Triggers**: Instantly reacts to specific window titles (e.g., distraction apps).

## How it Works

ASDGPT operates as a continuous loop:
1.  **Senses**: Monitors audio (speech rate, tone) and video (posture, activity).
2.  **Analyzes**: Sends aggregated data to a local Large Multi-modal Model (LMM).
3.  **Updates State**: Tracks 6 internal dimensions (Arousal, Sexual Arousal, Overload, Focus, Energy, Mood).
4.  **Intervenes**: Suggests micro-regulations (breathing, breaks) or creative actions (poses, captures) if state thresholds are crossed.
5.  **Learns**: You use hotkeys to mark interventions as "Helpful" or "Unhelpful".

## Setup and Installation

### System Requirements

*   **OS**: Windows, Linux, or macOS.
*   **Python**: 3.9 - 3.11 (Required for `TTS` package compatibility).
*   **Hardware**: Webcam and Microphone.
*   **System Libraries**:
    *   **Linux**: `x11-utils` (for window detection), `espeak` (TTS), `ffmpeg` (Audio), `portaudio19-dev` (Audio).
    *   **macOS**: `ffmpeg`, `portaudio`.
    *   **Windows**: Visual C++ Build Tools.

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
    If you want advanced voice cloning, ensure `TTS` is installed correctly. It is included in `requirements.txt`.

## Configuration

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

### Manual Configuration (`user_data/config.json`)

Example configuration for new features:
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
  "PERFORMANCE_MODE": "high",
  "ENABLE_MUSIC_CONTROL": false
}
```

### Music Integration (Spotify)

To enable music control:
1.  Set `ENABLE_MUSIC_CONTROL` to `true` in config (default is `false`).
2.  Ensure you have a way to handle `spotify:` URIs (official Spotify app installed).
3.  The system uses system commands (`open`, `start`, `spotify`) to trigger playlists.

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
*   **LMM Connection Errors (404/400):**
    *   Ensure your local LLM (e.g., LM Studio) is running.
    *   Check `LOCAL_LLM_URL` in config. It should usually be `http://127.0.0.1:1234`. The system automatically handles `/v1/chat/completions`.
    *   Verify `LOCAL_LLM_MODEL_ID` matches the loaded model name, or use `local-model` if generic.

## Testing

Run unit tests to verify installation:
```bash
python -m pytest tests/
```

### Stress Testing

To verify system reliability and clean shutdown behavior:
```bash
python tools/verify_crash.py
```
