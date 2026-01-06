import sounddevice as sd
import numpy as np
import time
import collections
import config # Potentially for audio device settings in the future

class AudioSensor:
    def __init__(self, data_logger=None, sample_rate=44100, chunk_duration=1.0, channels=1, history_seconds=5):
        self.logger = data_logger
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration # seconds
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.channels = channels

        # History buffers for advanced feature extraction
        self.history_size = int(history_seconds / chunk_duration)
        self.pitch_history = collections.deque(maxlen=self.history_size)
        self.rms_history = collections.deque(maxlen=self.history_size)

        # Audio buffer for speech rate analysis (needs more context than 1 chunk)
        # Store ~1 second of audio
        self.buffer_size = self.sample_rate * 1
        self.raw_audio_buffer = collections.deque(maxlen=self.buffer_size)

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
        # Ensure release is idempotent and robust
        if self.stream:
            self._log_info("Releasing audio stream.")
            try:
                if not self.stream.closed:
                    self.stream.stop()
                    self.stream.close()
            except Exception as e:
                # Even if stop/close fails, we consider it released
                self._log_error("Exception while releasing audio stream.", str(e))
            finally:
                self.stream = None

        self.error_state = False

    def has_error(self):
        return self.error_state

    def get_last_error(self):
        return self.last_error_message

    def _calculate_speech_rate(self, audio_data):
        """
        Estimates speech rate (syllables/sec) based on amplitude envelope peaks.
        Uses pure numpy to avoid scipy dependency.
        """
        try:
            # 1. Calculate Amplitude Envelope
            # Simple rectification + smoothing (low-pass filter)
            # Smoothing window: ~50ms to smooth out individual vibrations but keep syllable envelope
            window_size = int(0.05 * self.sample_rate)
            if len(audio_data) < window_size:
                return 0.0

            # Efficient moving average using numpy
            # We pad the signal to handle edges roughly or valid mode
            # Valid mode shortens the array, same mode pads with 0.
            # Simple convolution
            kernel = np.ones(window_size) / window_size
            envelope = np.convolve(np.abs(audio_data), kernel, mode='same')

            # 2. Find Peaks (Syllables) - Simple Numpy Implementation
            # Height: must be significant (e.g. > 1.5x mean RMS or a fixed silence threshold)
            # Distance: syllables are typically > 100-150ms apart.

            min_distance = int(0.15 * self.sample_rate)

            # Threshold: dynamic based on chunk RMS to handle varying volumes
            rms = np.sqrt(np.mean(audio_data**2))
            height_threshold = max(rms * 0.5, 0.02)

            # Find local maxima above threshold
            # 1. Identify candidates above threshold
            candidates = np.where(envelope > height_threshold)[0]

            if len(candidates) == 0:
                return 0.0

            # 2. Filter for local maxima
            # Basic peak finding: value > prev and value > next
            # Shifted arrays
            if len(envelope) < 3:
                return 0.0

            # Create a boolean mask for peaks
            # Note: this is a simple peak finder, adequate for envelope analysis
            is_peak = (envelope[1:-1] > envelope[:-2]) & (envelope[1:-1] > envelope[2:])
            peak_indices = np.where(is_peak)[0] + 1 # +1 because we sliced 1:-1

            # Filter by height again (redundant but safe)
            peak_indices = peak_indices[envelope[peak_indices] > height_threshold]

            # 3. Filter by distance (Greedy approach: pick peak, skip neighbors within distance)
            if len(peak_indices) == 0:
                return 0.0

            filtered_peaks = []
            last_peak_idx = -min_distance # Initialize so first peak is always valid

            # Sort by amplitude (descending) to prioritize prominent peaks?
            # Or just temporal order? Temporal is faster and usually fine for syllables.
            # Scipy finds all then removes neighbors. Let's do simple temporal.

            for idx in peak_indices:
                if idx - last_peak_idx >= min_distance:
                    filtered_peaks.append(idx)
                    last_peak_idx = idx

            # 4. Calculate Rate
            duration_sec = len(audio_data) / self.sample_rate
            return float(len(filtered_peaks) / duration_sec)

        except Exception as e:
            self._log_error(f"Error calculating speech rate: {e}")
            return 0.0

    def analyze_chunk(self, chunk):
        """
        Analyzes an audio chunk to extract features.
        Returns a dictionary of metrics: rms, spectral_centroid, pitch_estimation, zcr, pitch_variance, rms_variance, speech_rate.
        """
        metrics = {
            "rms": 0.0,
            "zcr": 0.0,
            "spectral_centroid": 0.0,
            "pitch_estimation": 0.0,
            "pitch_variance": 0.0,
            "rms_variance": 0.0,
            "activity_bursts": 0, # Legacy metric kept for backward compatibility
            "speech_rate": 0.0
        }

        if chunk is None or len(chunk) == 0:
            return metrics

        try:
            # Flatten if multi-channel (take first channel or average)
            if chunk.ndim > 1:
                audio_data = chunk[:, 0]
            else:
                audio_data = chunk

            # Update raw audio buffer for speech rate analysis
            self.raw_audio_buffer.extend(audio_data)

            # 1. RMS (Loudness)
            metrics["rms"] = float(np.sqrt(np.mean(audio_data**2)))

            # Normalize for other calculations (avoid div by zero, but handle silence)
            if metrics["rms"] < 1e-6:
                # Update history even for silence to reflect current state
                self.rms_history.append(metrics["rms"])

                # Check metrics that depend on history even if current frame is silence
                if len(self.rms_history) > 2:
                    rms_arr = np.array(self.rms_history)
                    metrics["rms_variance"] = float(np.std(rms_arr))

                    # Activity Bursts (approximate syllable/word clusters)
                    # Dynamic threshold: 80% of mean RMS
                    threshold = np.mean(rms_arr) * 0.8
                    if threshold > 1e-6: # Only calculate if there is some activity in history
                        above = rms_arr > threshold
                        if len(above) > 1:
                            crossings = np.sum(np.diff(above.astype(int)) > 0)
                            metrics["activity_bursts"] = int(crossings)

                # Return early for silence, but update rms_history first
                return metrics

            # 2. Zero Crossing Rate (ZCR) - Proxy for "noisiness" or high frequency content
            zero_crossings = np.nonzero(np.diff(audio_data > 0))[0]
            metrics["zcr"] = float(len(zero_crossings) / len(audio_data))

            # 3. Spectral Features (Centroid) using FFT
            # Windowing to reduce leakage
            windowed_data = audio_data * np.hanning(len(audio_data))
            spectrum = np.fft.rfft(windowed_data)
            magnitude = np.abs(spectrum)
            freqs = np.fft.rfftfreq(len(audio_data), d=1.0/self.sample_rate)

            # Spectral Centroid: center of mass of the spectrum
            sum_magnitude = np.sum(magnitude)
            if sum_magnitude > 1e-6:
                metrics["spectral_centroid"] = float(np.sum(freqs * magnitude) / sum_magnitude)

            # 4. Simple Pitch Estimation (Dominant Frequency)
            # Find peak frequency (ignoring very low freq DC/rumble < 50Hz)
            valid_idx = np.where(freqs > 50)[0]
            if len(valid_idx) > 0:
                peak_idx = valid_idx[np.argmax(magnitude[valid_idx])]
                metrics["pitch_estimation"] = float(freqs[peak_idx])

            # 5. Speech Rate (Syllable estimation using buffered audio)
            if len(self.raw_audio_buffer) >= int(0.5 * self.sample_rate): # Need at least 0.5s for meaningful rate
                buffered_audio = np.array(self.raw_audio_buffer)
                metrics["speech_rate"] = self._calculate_speech_rate(buffered_audio)

            # --- History / Time-Series Features ---
            self.rms_history.append(metrics["rms"])
            if metrics["pitch_estimation"] > 0:
                self.pitch_history.append(metrics["pitch_estimation"])

            # Pitch Variance (Intonation/Stress)
            if len(self.pitch_history) > 2:
                metrics["pitch_variance"] = float(np.std(list(self.pitch_history)))

            # RMS Variance
            if len(self.rms_history) > 2:
                rms_arr = np.array(self.rms_history)
                metrics["rms_variance"] = float(np.std(rms_arr))

                # Restore Activity Bursts
                threshold = np.mean(rms_arr) * 0.8
                if len(rms_arr) > 1 and threshold > 1e-6:
                    above = rms_arr > threshold
                    if len(above) > 1:
                        crossings = np.sum(np.diff(above.astype(int)) > 0)
                        metrics["activity_bursts"] = int(crossings)

        except Exception as e:
            self._log_error(f"Error extracting audio features: {e}")

        return metrics

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

    for i in range(5): # Try to get a few chunks
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
            # Test Analysis
            features = audio_sensor.analyze_chunk(audio_chunk)
            print(f"Analysis: RMS={features['rms']:.4f}, ZCR={features['zcr']:.4f}, Rate={features['speech_rate']:.2f}, Pitch={features['pitch_estimation']:.2f}Hz")

            # Add some processing delay
            time.sleep(0.1)
        else:
            # This means not enough data was available for a full chunk.
            print(f"Audio chunk {i+1} was None (not enough data or stream issue), no explicit error. Has_Error: {audio_sensor.has_error()}")
            time.sleep(0.2) # Wait a bit longer for data to fill

    audio_sensor.release()
    print("--- AudioSensor test finished ---")
