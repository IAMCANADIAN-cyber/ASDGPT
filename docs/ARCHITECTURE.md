# ASDGPT Architecture & Data Flow

This document details the internal architecture of ASDGPT (v2), explaining how sensor data flows through the system to generate state estimations, interventions, and interactive features.

## High-Level Overview

ASDGPT operates on a continuous feedback loop:
1.  **Sensors** capture raw audio, video, and active window data.
2.  **Logic Engine** processes this data into features, checks for triggers (including Meeting Mode and Sexual Arousal Mode), and coordinates logic.
3.  **Interaction Layer** handles voice commands (STT) and provides verbal feedback (TTS) or music control.
4.  **LMM (Large Multi-modal Model)** analyzes the context to estimate user state and suggest interventions.
5.  **State Engine** smooths and tracks the 6-dimensional user state.
6.  **Intervention Engine** executes actions (TTS, sounds, visual alerts).
7.  **User Feedback** (via hotkeys) reinforces or suppresses specific interventions.

---

## Core Components

### 1. Sensors (`sensors/`)
The system uses modular sensors to extract features before any AI processing occurs.

*   **AudioSensor** (`sensors/audio_sensor.py`):
    *   **Features**: `rms` (loudness), `zcr` (noisiness), `pitch_estimation`.
    *   **VAD (Voice Activity Detection)**: Determines `is_speech` to trigger STT or LMM analysis.
*   **VideoSensor** (`sensors/video_sensor.py`):
    *   **Features**: `video_activity` (motion intensity), `face_detected`, `face_count`.
    *   **Metrics**: `face_roll_angle` (head tilt), `posture_state`.
*   **WindowSensor** (`sensors/window_sensor.py`):
    *   **Function**: Detects the currently active application window title.
    *   **Privacy**: Automatically redacts sensitive information (e.g., "Password Manager" -> `[REDACTED]`).

### 2. Logic Engine (`core/logic_engine.py`)
The central coordinator ("The Brain"). It runs the main event loop.

*   **Triggers**: It decides *when* to call the expensive LMM.
    *   **High Audio Event**: Loudness > threshold AND identified as speech.
    *   **High Video Activity**: Motion > threshold AND face detected.
    *   **Periodic Check**: Heartbeat (default 5s) if no event occurs.
*   **Modes**:
    *   **Meeting Mode (Auto-DND)**: Automatically switches to "Do Not Disturb" if continuous speech + face + no input is detected.
    *   **Sexual Arousal Mode**: When `sexual_arousal` state exceeds `SEXUAL_AROUSAL_THRESHOLD`, the Logic Engine increases LMM sampling frequency (2x) to capture relevant context and potential content creation moments.
*   **Offline Fallback**:
    *   If the LMM circuit breaker is open (due to failures), triggers heuristic interventions directly.

### 3. Interaction Layer (`core/`)
New in v2, these components handle direct user interaction.

*   **STT Interface** (`core/stt_interface.py`):
    *   **Input**: Raw audio buffer from `LogicEngine`.
    *   **Engines**: `whisper` (Local, default) or `google` (Web API fallback).
    *   **Function**: Transcribes speech for Voice Commands (e.g., "Take a picture") and LMM context.
*   **Voice Interface** (`core/voice_interface.py`):
    *   **Output**: Text-to-Speech (TTS).
    *   **Engines**: `system` (pyttsx3/espeak) or `coqui` (Voice Cloning, optional).
    *   **Function**: Delivers verbal interventions or responses.
*   **Music Interface** (`core/music_interface.py`):
    *   **Function**: Controls background music based on `mood`, `arousal`, and `sexual_arousal` state.
    *   **Integration**: Uses system media keys or direct URI calls (e.g., `spotify:`).

### 4. LMM Integration (`core/lmm_interface.py`)
Interfaces with the local Large Language Model (e.g., deepseek via Oobabooga/LM Studio).

*   **Payload**: Bundles sensor metrics, the latest video frame (Base64), raw audio, active window, and recent speech context.
*   **Analysis**: Returns `state_estimation`, `visual_context` (tags), and `intervention_suggestion`.
*   **Reflexive Triggers**: Monitors `visual_context` tags for persistence (e.g., "phone_usage" > threshold) to trigger immediate interventions like `doom_scroll_breaker`.

### 5. Features & Integrations
Specialized modules for specific tasks.

*   **Social Media Manager** (`core/social_media_manager.py`):
    *   **Function**: Drafts local posts (image + JSON metadata) to `drafts/` folder.
    *   **AI Captioning**: Uses LMM to generate captions based on image context (e.g., "Late night vibes").
    *   **Note**: Does not post to external platforms automatically.
*   **Image Processing** (`core/image_processing.py`):
    *   **Digital PTZ**: "Pan-Tilt-Zoom" simulation. Crops high-resolution frames to center on the subject/face, creating a cinematic look for captures.

### 6. State Engine (`core/state_engine.py`)
Maintains the "Mental Model" of the user.

*   **6 Dimensions**: `Arousal`, `Overload`, `Focus`, `Energy`, `Mood`, `Sexual Arousal` (0-100 scale).
*   **Smoothing**: Applies a moving average to LMM outputs to prevent jitter.
*   **Note**: `Sexual Arousal` is distinct from physiological `Arousal` (alertness) and tracks erotic context.

### 7. Intervention Engine (`core/intervention_engine.py`)
Executes the actual "co-regulation" actions.

*   **Actions**: `speak` (via VoiceInterface), `play_sound`, `show_visual`.
*   **Prioritization**: System Triggers > LMM Suggestions.
*   **Escalation Policy**: Repeated triggers (within 60s) escalate the Intervention Tier (e.g., Tier 1 Message -> Tier 2 Chime + Message -> Tier 3 Urgent Tone). Escalation is monotonic (urgency only increases).
*   **Suppression**: Interventions marked "unhelpful" are blocked for a cooldown period. Centralized category cooldowns prevent log spam.

### 8. Feedback Loop
User feedback determines future system behavior.

*   **Inputs**: Hotkeys for "Helpful" (`Ctrl+Alt+Up`) and "Unhelpful" (`Ctrl+Alt+Down`).
*   **Logic**: Updates preference weights and suppresses unhelpful intervention types.

---

## Data Flow Diagram

```mermaid
graph TD
    User((User))
    Mic[Microphone] -->|Audio Chunk| LE{Logic Engine}
    Cam[Camera] -->|Video Frame| LE
    Win[Window System] -->|Active Window| LE

    LE -->|Audio Buffer| STT[STT Interface]
    STT -->|Transcribed Text| LE

    LE -->|Check Triggers| LE
    LE -->|Payload (Video+Audio+Text)| LMM[LMM Interface]

    LMM -->|State & Suggestion| LE
    LE -->|Update State| SE(State Engine)

    LE -->|Music Control| MI[Music Interface]
    MI -->|Playlist URI| Spotify

    LE -->|Action Request| IE{Intervention Engine}
    IE -->|Speak| VI[Voice Interface]
    VI -->|TTS Audio| User

    IE -->|Visual/Sound| User

    User -->|Feedback Hotkey| LE
```

## Configuration & Tuning

The system behavior is highly tunable via `config.py` or `user_data/config.json`. See `docs/CONFIGURATION.md` for a full reference.

Key v2 Configurations:
*   **Voice**: `TTS_ENGINE` ("system" vs "coqui"), `TTS_VOICE_CLONE_SOURCE`.
*   **Music**: `ENABLE_MUSIC_CONTROL`, `mood_playlists` (in code currently).
*   **Privacy**: `SENSITIVE_APP_KEYWORDS` for window title redaction.
