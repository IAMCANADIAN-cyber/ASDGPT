import sounddevice as sd
import numpy as np
import time
import collections
import queue
import threading
import config # Potentially for audio device settings in the future
from typing import Optional, Callable, Any

class AudioSensor:
    def __init__(self, data_logger=None, sample_rate=44100, chunk_duration=1.0, channels=1, history_seconds=5):
        self.logger = data_logger
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration # seconds
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.channels = channels
        self._lock = threading.RLock()

        # History buffers for advanced feature extraction
        self.history_size = int(history_seconds / chunk_duration)
        self.pitch_history = collections.deque(maxlen=self.history_size)
        self.rms_history = collections.deque(maxlen=self.history_size)

        # Audio buffer for speech rate analysis (needs more context than 1 chunk)
        # Store ~1 second of audio
        self.buffer_size = self.sample_rate * 1
        self.raw_audio_buffer = collections.deque(maxlen=self.buffer_size)

        # Thread-safe queue for audio chunks from callback
        self.internal_queue = queue.Queue(maxsize=10)

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
            if sd is None:
                 self._log_warning("sounddevice module not available.")
                 return
            devices = sd.query_devices()
            self._log_info(f"Available audio devices: {devices}")
            default_input = sd.query_devices(kind='input')
            if not default_input:
                 self._log_warning("No default input audio device found.")
            else:
                self._log_info(f"Default input audio device: {default_input}")
        except Exception as e:
            self._log_warning(f"Could not query audio devices: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream. Runs in a separate thread."""
        if status:
            self._log_warning(f"Audio callback status: {status}")

        if self.internal_queue.full():
            try:
                self.internal_queue.get_nowait() # Discard oldest
            except queue.Empty:
                pass

        try:
            self.internal_queue.put(indata.copy(), block=False)
        except queue.Full:
            pass # Should not happen due to discard logic above

    def _initialize_stream(self):
        with self._lock:
            if sd is None:
                self.error_state = True
                self.last_error_message = "sounddevice not available"
                return

            self._log_info(f"Attempting to initialize audio stream (SampleRate: {self.sample_rate}, Channels: {self.channels})...")
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    blocksize=self.chunk_size, # Read in chunks of desired size
                    # device=None, # Default input device
                    callback=self._audio_callback # Non-blocking callback
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
        # Check error state before locking to allow recovery logic to run
        if self.error_state:
            if time.time() - self.last_retry_time >= self.retry_delay:
                self._log_info("Attempting to re-initialize audio stream due to previous error...")
                self.release() # Ensure old stream is closed if any
                self._initialize_stream()

            if self.error_state: # If still in error state
                return None, self.last_error_message

        # We don't necessarily need the lock for the queue get,
        # but we should check if stream is active.
        # However, checking stream.closed might be race-prone without lock if release() is called.
        # But release() clears the queue, so get() would just return or empty.

        # Let's use lock for consistency with 'ours' approach, but only for state checks?
        # No, 'theirs' didn't use lock and relied on queue.
        # I'll stick to 'theirs' logic for get_chunk but add the lock for stream state check if we want to be strict.
        # But 'theirs' logic handles stream.closed check.

        if not self.stream or self.stream.closed:
            if not self.error_state:
                 self._log_error("Audio stream is not active or closed, though not in persistent error state.")
                 self.error_state = True
            return None, "Audio stream not available."

        try:
            # Get data from queue with timeout (slightly longer than chunk duration)
            # This ensures we don't block indefinitely if the callback stops firing
            timeout = self.chunk_duration * 2.0
            data_chunk = self.internal_queue.get(timeout=timeout)

            if self.error_state: # Was in error, but now working
                self._log_info("Audio sensor recovered and reading data.")
                self.error_state = False
                self.last_error_message = ""
            return data_chunk, None # Return audio data and no error

        except queue.Empty:
            # This indicates the callback isn't firing (hardware issue?)
            self.error_state = True
            error_msg = "Audio stream timeout: No data received from callback."
            self._log_error(error_msg)
            # We don't necessarily close the stream here, but we mark error to trigger retry logic
            # potentially in next call or via _handle_stream_error
            self._handle_stream_error()
            return None, error_msg

        except Exception as e:
            self.error_state = True
            error_msg = "Generic exception while getting audio chunk."
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
        with self._lock:
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

            # Clear queue to free memory
            while not self.internal_queue.empty():
                try:
                    self.internal_queue.get_nowait()
                except queue.Empty:
                    break

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

            # Check for flatness (Steady Hum / Tone rejection)
            # If the envelope has very low variance relative to its mean, it's a steady tone, not speech.
            env_mean = np.mean(envelope)
            env_std = np.std(envelope)
            if env_mean > 0 and (env_std / env_mean) < 0.3:
                 # Coefficient of variation < 0.3 implies fairly steady signal
                 return 0.0

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

    def calibrate(self, duration: float = 5.0, progress_callback: Optional[Callable[[float], None]] = None) -> float:
        """
        Records audio for a specified duration to calculate a personalized VAD silence threshold.
        Returns the suggested threshold (float).
        """
        self._log_info(f"Starting audio calibration for {duration}s...")
        start_time = time.time()
        rms_values = []

        # Clear initial buffer
        self.get_chunk()

        while time.time() - start_time < duration:
            chunk, err = self.get_chunk()
            if chunk is not None and len(chunk) > 0:
                metrics = self.analyze_chunk(chunk)
                rms = metrics.get('rms', 0.0)
                rms_values.append(rms)
                if progress_callback:
                    progress_callback(rms)
            elif err:
                self._log_warning(f"Calibration audio error: {err}")

            # Sleep slightly less than chunk duration to ensure we poll fast enough,
            # but relies on get_chunk blocking or returning None if not ready.
            # Here we sleep short to allow loop responsiveness.
            time.sleep(0.1)

        if not rms_values:
            self._log_warning("No audio data collected during calibration. returning default.")
            return getattr(config, 'VAD_SILENCE_THRESHOLD', 0.01)

        mean_rms = float(np.mean(rms_values))
        max_rms = float(np.max(rms_values))
        std_dev = float(np.std(rms_values)) if len(rms_values) > 1 else 0.0

        self._log_info(f"Calibration Stats - Mean: {mean_rms:.4f}, Max: {max_rms:.4f}, Std: {std_dev:.4f}")

        # Calculate threshold: Mean + 4 * StdDev (robust), or Max * 1.2 (safety margin)
        # Using 4 sigma to ensure we stay above the noise floor 99.9% of time.
        suggested_threshold = max(mean_rms + (4 * std_dev), max_rms * 1.2)

        # Clamp to reasonable minimum
        suggested_threshold = max(suggested_threshold, 0.005)

        self._log_info(f"Suggested VAD Silence Threshold: {suggested_threshold:.4f}")
        return suggested_threshold

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
            "speech_rate": 0.0,
            "is_speech": False,
            "speech_confidence": 0.0
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
            silence_thresh = getattr(config, 'VAD_SILENCE_THRESHOLD', 0.01)
            if metrics["rms"] < silence_thresh:
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
                # Explicitly set low confidence for silence
                metrics["speech_confidence"] = 0.0
                metrics["is_speech"] = False
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

            # 4. Pitch Estimation (Dominant Frequency with Parabolic Interpolation)
            # Find peak frequency (ignoring very low freq DC/rumble < 50Hz)
            valid_idx = np.where(freqs > 50)[0]
            if len(valid_idx) > 0:
                peak_bin = valid_idx[np.argmax(magnitude[valid_idx])]

                # Parabolic Interpolation for better precision
                if 0 < peak_bin < len(magnitude) - 1:
                    alpha = magnitude[peak_bin - 1]
                    beta = magnitude[peak_bin]
                    gamma = magnitude[peak_bin + 1]

                    denom = alpha - 2 * beta + gamma
                    if denom != 0:
                        delta = 0.5 * (alpha - gamma) / denom
                        true_bin = peak_bin + delta
                        metrics["pitch_estimation"] = float(true_bin * (self.sample_rate / len(audio_data)))
                    else:
                        metrics["pitch_estimation"] = float(freqs[peak_bin])
                else:
                    metrics["pitch_estimation"] = float(freqs[peak_bin])
                peak_idx = valid_idx[np.argmax(magnitude[valid_idx])]
                metrics["pitch_estimation"] = float(freqs[peak_idx])

            # 5. Speech Rate (Syllable estimation using buffered audio)
            if len(self.raw_audio_buffer) >= int(0.5 * self.sample_rate): # Need at least 0.5s for meaningful rate
                buffered_audio = np.array(self.raw_audio_buffer)
                metrics["speech_rate"] = self._calculate_speech_rate(buffered_audio)

            # --- Update History & Calculate Variances ---
            self.rms_history.append(metrics["rms"])
            if metrics["pitch_estimation"] > 0:
                self.pitch_history.append(metrics["pitch_estimation"])

            if len(self.pitch_history) > 2:
                metrics["pitch_variance"] = float(np.std(list(self.pitch_history)))

            if len(self.rms_history) > 2:
                rms_arr = np.array(self.rms_history)
                metrics["rms_variance"] = float(np.std(rms_arr))

                # Activity Bursts
                threshold = np.mean(rms_arr) * 0.8
                if len(rms_arr) > 1 and threshold > 1e-6:
                    above = rms_arr > threshold
                    if len(above) > 1:
                        crossings = np.sum(np.diff(above.astype(int)) > 0)
                        metrics["activity_bursts"] = int(crossings)

            # --- VAD Logic ---
            # Heuristics for human speech:
            # - Pitch: Typically 85-255Hz (Adult), can go up to ~600Hz (Child/Exclamation)
            # - ZCR: Voiced speech has low ZCR (< 0.3), Unvoiced (consonants) higher but usually < noise
            # - Spectral Centroid: Speech usually centered < 3000Hz? (Variable)

            confidence = 0.0

            # Factor 1: Pitch Validity
            # Broad range 60-600Hz to catch most human vocalizations
            has_pitch = 60 <= metrics["pitch_estimation"] <= 600
            if has_pitch:
                confidence += 0.5

            # Factor 2: ZCR
            # Low ZCR supports voiced speech. High ZCR often noise (or unvoiced consonants).
            if metrics["zcr"] < 0.2:
                confidence += 0.3 # Strong indicator of voiced speech if pitch is present
            elif metrics["zcr"] < 0.4:
                confidence += 0.1 # Moderate

            # Factor 3: RMS Variance (Speech is bursty/variable, fan noise is constant)
            if len(self.rms_history) > 3:
                 mean_rms = np.mean(list(self.rms_history))
                 rel_var = metrics["rms_variance"] / (mean_rms + 1e-6)

                 if rel_var > 0.2: # Variable volume (speech-like)
                     confidence += 0.2
                 elif rel_var < 0.05 and mean_rms > 0.01:
                     # VERY stable volume + significant energy = likely machine noise (fan/hum)
                     confidence -= 0.4

            metrics["speech_confidence"] = max(0.0, min(confidence, 1.0))

            # Thresholding
            # Default 0.5 confidence to be "speech"
            metrics["is_speech"] = metrics["speech_confidence"] > 0.4

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
