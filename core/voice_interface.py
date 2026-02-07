import platform
import threading
import os
import time
from typing import Optional
import config

# Imports
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from TTS.api import TTS
except ImportError:
    TTS = None

class VoiceInterface:
    """
    Handles Text-to-Speech (TTS) operations.
    Supports:
    - System TTS (via pyttsx3)
    - Coqui TTS (Voice Cloning) - Optional
    """

    def __init__(self, logger=None):
        self.logger = logger
        self._lock = threading.Lock()

        self.engine_type = getattr(config, 'TTS_ENGINE', 'system')

        # System TTS Setup
        self.pyttsx_engine = None
        if pyttsx3:
            try:
                # Initialize pyttsx3 (it needs to be on main thread typically, but we wrap calls)
                # Note: pyttsx3 on Linux (espeak) is fine in threads, but COM on Windows might have issues.
                # Usually we initialize it once.
                self.pyttsx_engine = pyttsx3.init()

                # Set Voice
                voice_id = getattr(config, 'TTS_VOICE_ID', None)
                if voice_id:
                    self._set_system_voice(voice_id)
            except Exception as e:
                self._log_warning(f"pyttsx3 initialization failed: {e}")

        # Coqui TTS Setup
        self.coqui_engine = None
        if self.engine_type == "coqui":
            if TTS:
                try:
                    model_name = getattr(config, 'TTS_MODEL_NAME', "tts_models/multilingual/multi-dataset/xtts_v2")
                    self._log_info(f"Loading Coqui TTS model: {model_name}...")
                    self.coqui_engine = TTS(model_name=model_name).to("cuda" if os.environ.get("USE_CUDA") == "1" else "cpu")
                    self._log_info("Coqui TTS loaded.")
                except Exception as e:
                    self._log_warning(f"Coqui TTS failed to load: {e}. Falling back to system.")
                    self.engine_type = "system"
            else:
                self._log_warning("Coqui TTS not installed. Falling back to system.")
                self.engine_type = "system"

    def _log_info(self, msg: str) -> None:
        if self.logger:
            self.logger.log_info(f"VoiceInterface: {msg}")
        else:
            print(f"VoiceInterface: {msg}")

    def _log_warning(self, msg: str) -> None:
        if self.logger:
            self.logger.log_warning(f"VoiceInterface: {msg}")
        else:
            print(f"VoiceInterface: {msg}")

    def _set_system_voice(self, voice_id: str):
        if not self.pyttsx_engine: return
        try:
            voices = self.pyttsx_engine.getProperty('voices')
            for voice in voices:
                if voice_id in voice.id or voice_id in voice.name:
                    self.pyttsx_engine.setProperty('voice', voice.id)
                    self._log_info(f"Selected system voice: {voice.name}")
                    return
            self._log_warning(f"System voice '{voice_id}' not found.")
        except Exception as e:
            self._log_warning(f"Error setting system voice: {e}")

    def speak(self, text: str, blocking: bool = True) -> None:
        """
        Public method to speak text.
        """
        if not text:
            return

        self._log_info(f"Speaking: '{text}'")

        if self.engine_type == "coqui" and self.coqui_engine:
            if blocking:
                self._speak_coqui(text)
            else:
                threading.Thread(target=self._speak_coqui, args=(text,), daemon=True).start()

        elif self.pyttsx_engine:
            # pyttsx3 runAndWait blocks
            if blocking:
                self._speak_system(text)
            else:
                threading.Thread(target=self._speak_system, args=(text,), daemon=True).start()
        else:
            self._log_warning("No TTS engine available.")

    def _speak_system(self, text: str) -> None:
        with self._lock:
            try:
                # Re-init if loop already closed (quirk of pyttsx3)
                # Actually, simpler to just use say() and runAndWait()
                self.pyttsx_engine.say(text)
                self.pyttsx_engine.runAndWait()
            except RuntimeError:
                # Loop already running?
                pass
            except Exception as e:
                self._log_warning(f"System TTS error: {e}")

    def _speak_coqui(self, text: str) -> None:
        with self._lock:
            try:
                # Clone path
                ref_path = getattr(config, 'TTS_VOICE_CLONE_SOURCE', None)
                output_file = "temp_tts_output.wav"

                if ref_path and os.path.exists(ref_path):
                    self.coqui_engine.tts_to_file(text=text, speaker_wav=ref_path, language="en", file_path=output_file)
                else:
                    # Generic or speaker name if multi-speaker but no clone
                    # Fallback to first speaker?
                    self.coqui_engine.tts_to_file(text=text, file_path=output_file)

                # Play audio
                # Using simple playback
                # We can reuse the play_sound logic or a simple os command
                # Ideally, InterventionEngine handles playback, but VoiceInterface is self contained here
                self._play_wav(output_file)

            except Exception as e:
                self._log_warning(f"Coqui TTS error: {e}")

    def _play_wav(self, path):
        # Fallback player
        try:
            if platform.system() == "Linux":
                os.system(f"aplay {path} > /dev/null 2>&1")
            elif platform.system() == "Darwin":
                os.system(f"afplay {path}")
            elif platform.system() == "Windows":
                # PowerShell play
                os.system(f'powershell -c (New-Object Media.SoundPlayer "{path}").PlaySync()')
        except:
            pass

    def stop(self) -> None:
        """Stops any active speech."""
        if self.pyttsx_engine:
            try:
                self.pyttsx_engine.stop()
            except:
                pass
