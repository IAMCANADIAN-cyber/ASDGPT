import speech_recognition as sr
import threading
import numpy as np
import io
import wave
from typing import Optional

class STTInterface:
    """
    Handles Speech-to-Text (STT) transcription.
    Currently uses SpeechRecognition (Google Web Speech API).
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.recognizer = sr.Recognizer()

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

    def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """
        Transcribes numpy audio data to text.
        """
        if audio_data is None or len(audio_data) == 0:
            return None

        try:
            # Convert numpy float32 to int16 (PCM) for SpeechRecognition
            # audio_data is typically normalized -1.0 to 1.0 from sounddevice
            audio_int16 = (audio_data * 32767).astype(np.int16)

            # Create an in-memory WAV file
            byte_io = io.BytesIO()
            with wave.open(byte_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2) # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())

            byte_io.seek(0)

            with sr.AudioFile(byte_io) as source:
                audio = self.recognizer.record(source)

            # Using Google Web Speech API (free default key)
            # For privacy/reliability, user could configure other engines here later
            text = self.recognizer.recognize_google(audio)
            self._log_info(f"Transcribed: '{text}'")
            return text

        except sr.UnknownValueError:
            self._log_info("Could not understand audio.")
            return None
        except sr.RequestError as e:
            self._log_warning(f"Could not request results from service; {e}")
            return None
        except Exception as e:
            self._log_warning(f"Transcription error: {e}")
            return None
