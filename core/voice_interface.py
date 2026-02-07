import platform
import subprocess
import threading
import os
import time
import base64
from typing import Optional, Dict, Any, List

# Placeholder for potential API-based TTS imports
# e.g., import elevenlabs, openai

class VoiceInterface:
    """
    Handles Text-to-Speech (TTS) operations.
    Designed to be modular:
    - Default: System TTS (say, espeak, PowerShell)
    - Future: API-based TTS (OpenAI, ElevenLabs)
    """

    def __init__(self, logger=None):
        self.logger = logger
        self._lock = threading.Lock()
        self._current_subprocess: Optional[subprocess.Popen] = None

        # Default configuration
        self.tts_engine = "system" # or "openai", "elevenlabs"

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

    def _log_error(self, msg: str) -> None:
        if self.logger:
            self.logger.log_error(f"VoiceInterface: {msg}")
        else:
            print(f"VoiceInterface: {msg}")

    def speak(self, text: str, blocking: bool = True) -> None:
        """
        Public method to speak text.
        """
        if not text:
            return

        self._log_info(f"Speaking: '{text}'")

        if self.tts_engine == "system":
            if blocking:
                self._speak_system(text)
            else:
                threading.Thread(target=self._speak_system, args=(text,), daemon=True).start()
        else:
            self._log_warning(f"TTS Engine '{self.tts_engine}' not implemented. Falling back to system.")
            if blocking:
                self._speak_system(text)
            else:
                threading.Thread(target=self._speak_system, args=(text,), daemon=True).start()

    def _speak_system(self, text: str) -> None:
        """
        Uses platform-specific TTS commands.
        """
        system = platform.system()
        command = []

        if system == "Darwin":  # macOS
            command = ["say", text]
        elif system == "Linux":
            # Try espeak or spd-say
            command = ["espeak", text] # Default to espeak
        elif system == "Windows":
            # PowerShell with SINGLE QUOTES to prevent variable expansion injection
            # In PowerShell '...' treats content literally (no $var expansion)
            # To escape a single quote inside single quotes, use two single quotes ''
            safe_text = text.replace("'", "''")
            ps_cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')"
            command = ["powershell", "-Command", ps_cmd]

        if not command:
             return

        try:
            with self._lock:
                # Use Popen to allow interruption
                self._current_subprocess = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            if self._current_subprocess:
                self._current_subprocess.wait()

        except FileNotFoundError:
            # If linux default failed, try fallback
            if system == "Linux" and command[0] == "espeak":
                    try:
                        command = ["spd-say", text]
                        with self._lock:
                            self._current_subprocess = subprocess.Popen(
                                command,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                        if self._current_subprocess:
                            self._current_subprocess.wait()
                    except Exception as e:
                        self._log_warning(f"TTS fallback failed: {e}")
        except Exception as e:
            self._log_warning(f"TTS failed: {e}")
        finally:
            with self._lock:
                self._current_subprocess = None

    def stop(self) -> None:
        """Stops any active speech."""
        with self._lock:
            if self._current_subprocess:
                self._log_info("Terminating active TTS subprocess.")
                try:
                    self._current_subprocess.terminate()
                except Exception as e:
                    self._log_warning(f"Error terminating TTS subprocess: {e}")
