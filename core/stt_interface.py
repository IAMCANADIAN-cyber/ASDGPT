import threading
import numpy as np
import io
import wave
from typing import Optional
import os
import warnings

# Imports for speech engines
try:
    with warnings.catch_warnings():
        # Suppress DeprecationWarning from speech_recognition (aifc, audioop) for Python 3.13 compatibility
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        import speech_recognition as sr
except ImportError:
    sr = None

try:
    import whisper
except ImportError:
    whisper = None

try:
    import torch
except ImportError:
    torch = None

class STTInterface:
    """
    Handles Speech-to-Text (STT) transcription.
    Supports:
    - Google Web Speech API (via SpeechRecognition)
    - Local Whisper (via openai-whisper)
    """

    def __init__(self, logger=None, model_size="base"):
        self.logger = logger
        self.engine = "whisper" if whisper else "google" # Default to whisper if available
        self.recognizer = sr.Recognizer() if sr else None

        # Whisper setup
        self.whisper_model = None
        self.model_size = model_size

        # Lazy loading of Whisper to avoid startup delay if not used
        # or load now if engine is whisper
        if self.engine == "whisper":
            self._load_whisper()

    def _log_info(self, msg: str) -> None:
        if self.logger:
            self.logger.log_info(f"STTInterface: {msg}")
        else:
            print(f"STTInterface: {msg}")

    def _log_warning(self, msg: str) -> None:
        if self.logger:
            self.logger.log_warning(f"STTInterface: {msg}")
        else:
            print(f"STTInterface: {msg}")

    def _load_whisper(self):
        if not whisper:
            self._log_warning("openai-whisper not installed. Falling back to Google API.")
            self.engine = "google"
            return

        try:
            self._log_info(f"Loading local Whisper model ({self.model_size})...")
            # Check for GPU
            device = "cuda" if torch and torch.cuda.is_available() else "cpu"
            self.whisper_model = whisper.load_model(self.model_size, device=device)
            self._log_info(f"Whisper model loaded on {device}.")
        except Exception as e:
            self._log_warning(f"Failed to load Whisper model: {e}. Falling back to Google API.")
            self.engine = "google"

    def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """
        Transcribes numpy audio data to text.
        audio_data: float32 numpy array (-1.0 to 1.0)
        """
        if audio_data is None or len(audio_data) == 0:
            return None

        # 1. Local Whisper Path
        if self.engine == "whisper" and self.whisper_model:
            try:
                # Whisper expects float32 audio at 16kHz
                # We need to resample if sample_rate != 16000
                audio_for_whisper = audio_data.flatten().astype(np.float32)

                if sample_rate != 16000:
                    # Simple resampling using linear interpolation (fast, adequate for STT)
                    # OR usage of scipy.signal.resample if available
                    # Let's check for scipy/torch audio transforms?
                    # Minimal dependency approach: use numpy interpolation
                    duration_sec = len(audio_for_whisper) / sample_rate
                    target_length = int(duration_sec * 16000)

                    # Create time axes
                    x_old = np.linspace(0, duration_sec, len(audio_for_whisper))
                    x_new = np.linspace(0, duration_sec, target_length)

                    audio_for_whisper = np.interp(x_new, x_old, audio_for_whisper).astype(np.float32)

                # Transcribe
                # no_speech_threshold default is 0.6
                result = self.whisper_model.transcribe(audio_for_whisper, fp16=False) # fp16=False for CPU compatibility safety
                text = result.get("text", "").strip()

                if text:
                    self._log_info(f"Whisper Transcribed: '{text}'")
                    return text
                return None

            except Exception as e:
                self._log_warning(f"Whisper transcription error: {e}")
                return None

        # 2. Google Web Speech API Path (Fallback)
        if self.recognizer:
            try:
                # Convert float32 to int16 PCM for SR
                audio_int16 = (audio_data * 32767).astype(np.int16)

                byte_io = io.BytesIO()
                with wave.open(byte_io, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_int16.tobytes())

                byte_io.seek(0)
                with sr.AudioFile(byte_io) as source:
                    audio = self.recognizer.record(source)

                text = self.recognizer.recognize_google(audio)
                self._log_info(f"Google Transcribed: '{text}'")
                return text

            except sr.UnknownValueError:
                # self._log_info("Google could not understand audio.")
                return None
            except Exception as e:
                self._log_warning(f"Google transcription error: {e}")
                return None

        return None
