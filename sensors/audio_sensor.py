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
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size, # Read in chunks of desired size
                # device=None, # Default input device
                callback=None # Using blocking read, so no callback
            )
            self.stream.start() # Start the stream
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
            # With a blocking stream (no callback), read() will wait until it has enough data.
            data_chunk, overflowed = self.stream.read(self.chunk_size)
            if overflowed:
                self._log_warning("Audio buffer overflow detected during read.")

            if self.error_state: # Was in error, but now working
                self._log_info("Audio sensor recovered and reading data.")
                self.error_state = False
                self.last_error_message = ""
            return data_chunk, None # Return audio data and no error

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

if __name__ == '__main__':
    class MockDataLogger:
        def log_info(self, msg): print(f"MOCK_LOG_INFO: {msg}")
        def log_warning(self, msg): print(f"MOCK_LOG_WARN: {msg}")
        def log_error(self, msg, details=""): print(f"MOCK_LOG_ERROR: {msg} | Details: {details}")

    mock_logger = MockDataLogger()

    print("--- Testing AudioSensor ---")
    # Reduce chunk duration for faster testing if desired, but ensure it's not too small.
    audio_sensor = AudioSensor(data_logger=mock_logger, chunk_duration=0.5)

    if audio_sensor.has_error():
        print(f"Initial error: {audio_sensor.get_last_error()}")
        print(f"Will attempt retry after {audio_sensor.retry_delay} seconds if get_chunk is called.")

    for i in range(10): # Try to get a few chunks
        print(f"\nAttempting to get audio chunk {i+1}...")
        # Need to wait for buffer to fill if chunk_duration is long
        # time.sleep(audio_sensor.chunk_duration / 2) # Wait a bit for data to accumulate

        audio_chunk, error = audio_sensor.get_chunk()

        if error:
            print(f"Error getting audio chunk: {error}")
            if audio_sensor.has_error() and i < 2:
                print(f"Sensor in error state. Waiting for {audio_sensor.retry_delay + 1}s to allow retry logic...")
                time.sleep(audio_sensor.retry_delay + 1)
            elif audio_sensor.has_error():
                 print("Sensor still in error state. Continuing test without long wait.")
                 time.sleep(0.1)

        elif audio_chunk is not None:
            print(f"Audio chunk {i+1} received successfully. Shape: {audio_chunk.shape}, Max val: {np.max(audio_chunk):.4f}")
            # Add some processing delay
            time.sleep(0.1)
        else:
            # This means not enough data was available for a full chunk.
            print(f"Audio chunk {i+1} was None (not enough data or stream issue), no explicit error. Has_Error: {audio_sensor.has_error()}")
            time.sleep(0.2) # Wait a bit longer for data to fill

    audio_sensor.release()
    print("--- AudioSensor test finished ---")
