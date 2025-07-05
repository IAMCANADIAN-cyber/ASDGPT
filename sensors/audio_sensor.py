import sounddevice as sd
import numpy as np
import time
import config # Potentially for audio device settings in the future

class AudioSensor:
    def __init__(self, data_logger=None, sample_rate=44100, chunk_duration=1.0, channels=1):
        self.logger = data_logger
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration # seconds
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.channels = channels

        self.stream = None
        self.error_state = False
        self.last_error_message = ""
        self.retry_delay = 30  # seconds
        self.last_retry_time = 0

        self._check_devices()
        self._initialize_stream()

    def _log_info(self, message):
        if self.logger: self.logger.log_info(f"AudioSensor: {message}")
        else: print(f"INFO: AudioSensor: {message}")

    def _log_warning(self, message):
        if self.logger: self.logger.log_warning(f"AudioSensor: {message}")
        else: print(f"WARNING: AudioSensor: {message}")

    def _log_error(self, message, details=""):
        full_message = f"AudioSensor: {message}"
        if self.logger: self.logger.log_error(full_message, details)
        else: print(f"ERROR: {full_message} | Details: {details}")
        self.last_error_message = message

    def _check_devices(self):
        try:
            devices = sd.query_devices()
            self._log_info(f"Available audio devices: {devices}")
            default_input = sd.query_devices(kind='input')
            if not default_input:
                 self._log_warning("No default input audio device found.")
                 # This might not be an error yet if a specific device is chosen later or if it's non-critical
            else:
                self._log_info(f"Default input audio device: {default_input}")
        except Exception as e:
            self._log_warning(f"Could not query audio devices: {e}")


    def _initialize_stream(self):
        self._log_info(f"Attempting to initialize audio stream (SampleRate: {self.sample_rate}, Channels: {self.channels})...")
        try:
            # Define a dummy callback as InputStream needs one, though we might not use it traditionally
            def audio_callback(indata, frames, time, status):
                if status:
                    self._log_warning(f"Audio callback status: {status}")
                # We are not processing data in this callback for this example's get_chunk model
                pass

            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size, # Read in chunks of desired size
                # device=None, # Default input device
                callback=audio_callback # Even if not used for data below, good for status
            )
            self.stream.start() # Start the stream
            self.error_state = False
            self.last_error_message = ""
            self._log_info("Audio stream initialized and started successfully.")

            # Try reading a small chunk to confirm
            # data_chunk, overflowed = self.stream.read(self.chunk_size) # sd.InputStream.read is blocking
            # if overflowed:
            #    self._log_warning("Initial audio read reported overflow.")
            # self._log_info(f"Initial audio chunk read successfully, shape: {data_chunk.shape}")


        except Exception as e:
            self.error_state = True
            error_msg = "Exception during audio stream initialization."
            self._log_error(error_msg, str(e))
            if self.stream:
                try:
                    if not self.stream.closed:
                        self.stream.stop()
                        self.stream.close()
                except Exception as close_e:
                    self._log_error("Exception while closing errored audio stream.", str(close_e))
            self.stream = None

        self.last_retry_time = time.time()

    def get_chunk(self):
        if self.error_state:
            if time.time() - self.last_retry_time >= self.retry_delay:
                self._log_info("Attempting to re-initialize audio stream due to previous error...")
                self.release() # Ensure old stream is closed if any
                self._initialize_stream()

            if self.error_state: # If still in error state
                return None, self.last_error_message

        if not self.stream or self.stream.closed:
            if not self.error_state:
                 self._log_error("Audio stream is not active or closed, though not in persistent error state.")
                 self.error_state = True
            return None, "Audio stream not available."

        try:
            # sd.InputStream.read is blocking until `self.chunk_size` frames are read.
            # Make sure blocksize in constructor matches read size for simplicity here.
            if self.stream.read_available >= self.chunk_size:
                data_chunk, overflowed = self.stream.read(self.chunk_size)
                if overflowed:
                    self._log_warning("Audio buffer overflow detected during read.")

                if self.error_state: # Was in error, but now working
                    self._log_info("Audio sensor recovered and reading data.")
                    self.error_state = False
                    self.last_error_message = ""
                return data_chunk, None # Return audio data and no error
            else:
                # Not enough data available for a non-blocking read.
                # For this example, we'll treat it as "no new chunk yet" rather than an error.
                # A real implementation might queue smaller reads or handle this differently.
                # print(f"AudioSensor: Not enough data available ({self.stream.read_available}/{self.chunk_size}). Returning None.")
                return None, None # No new full chunk, not an error

        except sd.PortAudioError as pae:
            self.error_state = True
            error_msg = f"PortAudioError while reading audio chunk: {pae}"
            self._log_error(error_msg)
            # Attempt to gracefully stop and close the stream on PortAudioError
            self._handle_stream_error()
            return None, error_msg
        except Exception as e:
            self.error_state = True
            error_msg = "Generic exception while reading audio chunk."
            self._log_error(error_msg, str(e))
            self._handle_stream_error()
            return None, error_msg

    def _handle_stream_error(self):
        if self.stream and not self.stream.closed:
            try:
                self.stream.stop()
                self.stream.close()
                self._log_info("Audio stream stopped and closed due to error.")
            except Exception as e:
                self._log_error("Exception during emergency closure of audio stream.", str(e))
        self.stream = None # Ensure stream is marked as None after closure


    def release(self):
        if self.stream and not self.stream.closed:
            self._log_info("Releasing audio stream.")
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                self._log_error("Exception while releasing audio stream.", str(e))
        self.stream = None
        self.error_state = False

    def has_error(self):
        return self.error_state

    def get_last_error(self):
        return self.last_error_message

import json
from vosk import Model, KaldiRecognizer, SetLogLevel

class AudioSensor:
    def __init__(self, data_logger=None, sample_rate=44100, chunk_duration=1.0, channels=1, vosk_model_path=None):
        self.logger = data_logger
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration # seconds
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.channels = channels
        if self.channels != 1:
            self._log_warning("Vosk works best with mono audio. Received non-mono channel count.")
            # Consider converting to mono if necessary, or ensure input is mono.

        self.stream = None
        self.error_state = False
        self.last_error_message = ""
        self.retry_delay = 30  # seconds
        self.last_retry_time = 0

        # Vosk STT specific
        self.vosk_model_path = vosk_model_path
        self.vosk_model = None
        self.vosk_recognizer = None
        self._initialize_vosk()

        self._check_devices()
        self._initialize_stream()

    def _initialize_vosk(self):
        if not self.vosk_model_path:
            # Try a default path or inform the user. For now, we'll make it optional
            # and STT methods will fail if not initialized.
            # A better approach might be to download a default model or guide the user.
            self._log_warning("Vosk model path not provided. STT functionality will be disabled.")
            # Example: self.vosk_model_path = "vosk-model-small-en-us-0.15"
            # Users would need to download this and place it appropriately.
            # Or, we could integrate a downloader.
            return

        try:
            SetLogLevel(-1) # Suppress verbose Vosk logging. Set to 0 for more info.
            self.vosk_model = Model(self.vosk_model_path)
            self.vosk_recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
            self._log_info(f"Vosk model loaded successfully from {self.vosk_model_path}.")
        except Exception as e:
            self._log_error(f"Failed to initialize Vosk model from {self.vosk_model_path}.", str(e))
            self.vosk_model = None
            self.vosk_recognizer = None
            self.error_state = True # Consider a specific STT error state
            self.last_error_message = f"Vosk init failed: {e}"

    def _log_info(self, message):
        if self.logger: self.logger.log_info(f"AudioSensor: {message}")
        else: print(f"INFO: AudioSensor: {message}")

    def _log_warning(self, message):
        if self.logger: self.logger.log_warning(f"AudioSensor: {message}")
        else: print(f"WARNING: AudioSensor: {message}")

    def _log_error(self, message, details=""):
        full_message = f"AudioSensor: {message}"
        if self.logger: self.logger.log_error(full_message, details)
        else: print(f"ERROR: {full_message} | Details: {details}")
        self.last_error_message = message

    def _check_devices(self):
        try:
            devices = sd.query_devices()
            self._log_info(f"Available audio devices: {devices}")
            default_input = sd.query_devices(kind='input')
            if not default_input:
                 self._log_warning("No default input audio device found.")
            else:
                self._log_info(f"Default input audio device: {default_input}")
        except Exception as e:
            self._log_warning(f"Could not query audio devices: {e}")


    def _initialize_stream(self):
        self._log_info(f"Attempting to initialize audio stream (SampleRate: {self.sample_rate}, Channels: {self.channels})...")
        try:
            def audio_callback(indata, frames, time, status):
                if status:
                    self._log_warning(f"Audio callback status: {status}")
                # We are not processing data in this callback for this example's get_chunk model
                pass

            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                # device=None, # Default input device
                callback=audio_callback
            )
            self.stream.start()
            self.error_state = False
            self.last_error_message = ""
            self._log_info("Audio stream initialized and started successfully.")

        except Exception as e:
            self.error_state = True
            error_msg = "Exception during audio stream initialization."
            self._log_error(error_msg, str(e))
            if self.stream:
                try:
                    if not self.stream.closed:
                        self.stream.stop()
                        self.stream.close()
                except Exception as close_e:
                    self._log_error("Exception while closing errored audio stream.", str(close_e))
            self.stream = None
        self.last_retry_time = time.time()

    def get_chunk(self):
        if self.error_state and "Vosk init failed" not in self.last_error_message : # Don't retry stream if Vosk itself failed init
            if time.time() - self.last_retry_time >= self.retry_delay:
                self._log_info("Attempting to re-initialize audio stream due to previous error...")
                self.release_stream_only()
                self._initialize_stream()

            if self.error_state and "Vosk init failed" not in self.last_error_message:
                return None, self.last_error_message

        if not self.stream or self.stream.closed:
            if not self.error_state: # If not already in a persistent error state like Vosk init failure
                 self._log_error("Audio stream is not active or closed, though not in persistent error state.")
                 self.error_state = True # Mark as error to trigger potential recovery
            return None, "Audio stream not available."

        try:
            if self.stream.read_available >= self.chunk_size:
                data_chunk, overflowed = self.stream.read(self.chunk_size)
                if overflowed:
                    self._log_warning("Audio buffer overflow detected during read.")

                # Convert to bytes for Vosk if it's float (sounddevice default)
                # Vosk expects 16-bit PCM audio data.
                if data_chunk.dtype == np.float32 or data_chunk.dtype == np.float64:
                    data_chunk = (data_chunk * 32767).astype(np.int16)

                audio_bytes = data_chunk.tobytes()

                if self.error_state and "Vosk init failed" not in self.last_error_message:
                    self._log_info("Audio sensor recovered and reading data.")
                    self.error_state = False # Reset general error state if it wasn't a Vosk init issue
                    self.last_error_message = ""
                return audio_bytes, None # Return audio data as bytes and no error
            else:
                return None, None

        except sd.PortAudioError as pae:
            self.error_state = True
            error_msg = f"PortAudioError while reading audio chunk: {pae}"
            self._log_error(error_msg)
            self._handle_stream_error()
            return None, error_msg
        except Exception as e:
            self.error_state = True
            error_msg = "Generic exception while reading audio chunk."
            self._log_error(error_msg, str(e))
            self._handle_stream_error()
            return None, error_msg

    def transcribe_chunk(self, audio_bytes=None):
        """
        Transcribes a chunk of audio data using Vosk.
        If audio_bytes is None, it will attempt to get a new chunk.
        Returns the transcribed text or None if no speech is detected or an error occurs.
        """
        if not self.vosk_recognizer:
            # self._log_warning("Vosk recognizer not initialized. Cannot transcribe.")
            return None, "Vosk recognizer not initialized."

        if audio_bytes is None:
            audio_bytes, error = self.get_chunk()
            if error:
                return None, error
            if audio_bytes is None: # No new chunk available
                return None, None

        try:
            if self.vosk_recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(self.vosk_recognizer.Result())
                if result.get("text"):
                    self._log_info(f"Transcription (partial/final): {result['text']}")
                    return result["text"], None
            else:
                partial_result = json.loads(self.vosk_recognizer.PartialResult())
                if partial_result.get("partial") and len(partial_result["partial"]) > 0:
                    # self._log_info(f"Transcription (partial): {partial_result['partial']}")
                    return partial_result["partial"], "partial" # Indicate partial result
            return None, None # No text detected in this chunk or only silence
        except Exception as e:
            self._log_error("Exception during Vosk transcription.", str(e))
            return None, f"Vosk transcription error: {e}"

    def get_final_transcription(self):
        """
        Forces Vosk to finalize the current utterance and return the transcription.
        Useful at the end of a speech segment.
        """
        if not self.vosk_recognizer:
            # self._log_warning("Vosk recognizer not initialized. Cannot get final transcription.")
            return None, "Vosk recognizer not initialized."
        try:
            result = json.loads(self.vosk_recognizer.FinalResult())
            if result.get("text"):
                self._log_info(f"Transcription (final): {result['text']}")
                return result["text"], None
            return None, None # No text
        except Exception as e:
            self._log_error("Exception during Vosk FinalResult.", str(e))
            return None, f"Vosk FinalResult error: {e}"


    def _handle_stream_error(self):
        if self.stream and not self.stream.closed:
            try:
                self.stream.stop()
                self.stream.close()
                self._log_info("Audio stream stopped and closed due to error.")
            except Exception as e:
                self._log_error("Exception during emergency closure of audio stream.", str(e))
        self.stream = None

    def release_stream_only(self):
        if self.stream and not self.stream.closed:
            self._log_info("Releasing audio stream component.")
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                self._log_error("Exception while releasing audio stream component.", str(e))
        self.stream = None
        # Don't reset general error_state if it might be due to Vosk init
        if "Vosk init failed" not in self.last_error_message:
            self.error_state = False


    def release(self):
        self.release_stream_only()
        # No specific release for Vosk model/recognizer objects needed beyond Python's GC
        # unless there are specific C library handles, but vosk-python handles this.
        self._log_info("AudioSensor released (including STT if initialized).")
        self.vosk_recognizer = None
        self.vosk_model = None


    def has_error(self):
        return self.error_state

    def get_last_error(self):
        return self.last_error_message

if __name__ == '__main__':
    class MockDataLogger:
        def log_info(self, msg): print(f"INFO: {msg}")
        def log_warning(self, msg): print(f"WARN: {msg}")
        def log_error(self, msg, details=""): print(f"ERROR: {msg} | Details: {details}")

    mock_logger = MockDataLogger()

    print("--- Testing AudioSensor with STT ---")

    # IMPORTANT: User needs to download a Vosk model and provide the path.
    # For example, download 'vosk-model-small-en-us-0.15' from https://alphacephei.com/vosk/models
    # and unzip it to a known location.
    # Update this path to your local model path.
    VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15" # Replace with actual path if not in current dir
    # Check if model path exists, otherwise skip STT part of test
    import os
    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"WARN: Vosk model not found at '{VOSK_MODEL_PATH}'. STT tests will be limited.")
        print("Please download a Vosk model (e.g., vosk-model-small-en-us-0.15) and place it in the project directory or provide the correct path.")
        stt_enabled_for_test = False
    else:
        stt_enabled_for_test = True

    audio_sensor = AudioSensor(
        data_logger=mock_logger,
        chunk_duration=1.0, # Process 1-second chunks for STT
        vosk_model_path=VOSK_MODEL_PATH if stt_enabled_for_test else None
    )

    if audio_sensor.has_error() and "Vosk init failed" in audio_sensor.get_last_error():
        print(f"Vosk initialization failed: {audio_sensor.get_last_error()}. Aborting STT test part.")
        stt_enabled_for_test = False # Disable STT part of test
    elif audio_sensor.has_error():
         print(f"Initial stream error: {audio_sensor.get_last_error()}")


    print("\nSpeak into your microphone for a few seconds if STT is enabled...")
    if not stt_enabled_for_test:
        print("(STT is currently disabled for this test run as model path was not found or init failed)")

    all_transcribed_text = []

    for i in range(15): # Try to get a few chunks and transcribe
        print(f"\n--- Cycle {i+1} ---")

        audio_bytes, error = audio_sensor.get_chunk()

        if error:
            print(f"Error getting audio chunk: {error}")
            if audio_sensor.has_error() and "Vosk" not in error and i < 2 : # If stream error, try to let it recover
                print(f"Sensor in stream error state. Waiting for {audio_sensor.retry_delay + 1}s to allow retry logic...")
                time.sleep(audio_sensor.retry_delay + 1)
            else:
                time.sleep(0.1) # Brief pause
            continue

        if audio_bytes is not None:
            print(f"Audio chunk received successfully, {len(audio_bytes)} bytes.")
            if stt_enabled_for_test:
                transcribed_text, stt_error = audio_sensor.transcribe_chunk(audio_bytes)
                if stt_error and stt_error != "partial":
                    print(f"STT Error: {stt_error}")
                elif transcribed_text:
                    print(f"STT (chunk result): '{transcribed_text}' (type: {'partial' if stt_error == 'partial' else 'likely final in chunk'})")
                    if stt_error != "partial" and transcribed_text not in all_transcribed_text: # Avoid duplicate final results from same chunk
                        all_transcribed_text.append(transcribed_text)
                else:
                    print("STT: No text detected in this chunk or silence.")
        else:
            print("No audio chunk available this cycle.")
            if not audio_sensor.stream or audio_sensor.stream.closed:
                print("Stream seems to be closed. Waiting for potential recovery...")
                time.sleep(1)


        time.sleep(0.5) # Simulate some time between processing chunks

    if stt_enabled_for_test:
        final_text, final_err = audio_sensor.get_final_transcription()
        if final_err:
            print(f"STT Final Error: {final_err}")
        elif final_text:
            print(f"\nSTT (FinalResult): '{final_text}'")
            if final_text not in all_transcribed_text:
                 all_transcribed_text.append(final_text)
        else:
            print("\nSTT (FinalResult): No final text.")

        print("\n--- Summary of Transcriptions ---")
        if all_transcribed_text:
            full_sentence = " ".join(all_transcribed_text)
            print(f"Potentially combined: {full_sentence}")
        else:
            print("No text was transcribed.")

    audio_sensor.release()
    print("\n--- AudioSensor with STT test finished ---")
