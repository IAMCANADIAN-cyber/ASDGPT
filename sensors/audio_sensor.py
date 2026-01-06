import sounddevice as sd
import numpy as np
import time
import threading
import queue

class AudioSensor:
    def __init__(self, data_logger=None, logger=None, sample_rate=44100, chunk_duration=1.0, channels=1, history_seconds=5):
        # Support both logger arguments for backward compatibility
        self.logger = data_logger if data_logger else logger
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
        self.is_running = False
        self.audio_thread = None
        self.lock = threading.Lock()

        # Audio Configuration
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_duration = float(history_seconds)
        self.buffer_size = int(self.sample_rate * self.buffer_duration)
        self.chunk_size = int(self.sample_rate * 0.1) # 100ms chunks for callback/internal queue

        # Buffers
        self.raw_audio_buffer = np.zeros((self.buffer_size, self.channels), dtype=np.float32)

        # Internal queue for blocking get_chunk behavior (legacy support)
        # We put small chunks here so get_chunk can retrieve them
        self.chunk_queue = queue.Queue(maxsize=20)

        # Auto-start for backward compatibility
        self.start()

    def start(self):
        if self.is_running:
            return

        self.is_running = True
        self.audio_thread = threading.Thread(target=self._capture_loop)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        if self.logger:
            self.logger.log_event("sensor_start", "Audio sensor started")

    def stop(self):
        self.is_running = False
        if self.audio_thread:
            self.audio_thread.join()
        if self.logger:
            self.logger.log_event("sensor_stop", "Audio sensor stopped")

    def _capture_loop(self):
        def callback(indata, frames, time_info, status):
            if status and self.logger:
                self.logger.log_event("audio_error", str(status))

            # 1. Update Ring Buffer (for Analysis)
            with self.lock:
                length = len(indata)
                if length > self.buffer_size:
                    self.raw_audio_buffer = indata[-self.buffer_size:]
                else:
                    self.raw_audio_buffer = np.roll(self.raw_audio_buffer, -length, axis=0)
                    self.raw_audio_buffer[-length:] = indata

            # 2. Feed Chunk Queue (for legacy get_chunk blocking read)
            try:
                # We copy indata to avoid reference issues if sounddevice reuses buffers
                self.chunk_queue.put_nowait(indata.copy())
            except queue.Full:
                # If queue is full, drop oldest
                try:
                    self.chunk_queue.get_nowait()
                    self.chunk_queue.put_nowait(indata.copy())
                except:
                    pass

        while self.is_running:
            try:
                with sd.InputStream(callback=callback, channels=self.channels, samplerate=self.sample_rate, blocksize=self.chunk_size):
                    while self.is_running:
                        sd.sleep(100)
            except Exception as e:
                if self.logger:
                    self.logger.log_event("audio_fatal_error", f"Could not open stream: {e}")

                # Retry logic
                time.sleep(5)

    def get_chunk(self):
        """
        Legacy method for backward compatibility.
        Blocks until a new chunk is available, mimicking blocking read.
        """
        try:
            # Block with timeout to allow checking is_running
            chunk = self.chunk_queue.get(timeout=1.0)
            return chunk, None
        except queue.Empty:
            if not self.is_running:
                return None, "Sensor stopped"
            # Return None but no error if just timed out (no data yet)
            return None, None

    def get_metrics(self):
        # 1. Acquire lock to copy data
        with self.lock:
            # Analyze last 1 second
            one_sec_samples = int(self.sample_rate * 1.0)
            chunk = self.raw_audio_buffer[-one_sec_samples:].copy()

        # 2. Analyze data without lock (heavy lifting)
        return self.analyze_chunk(chunk)

    def release(self):
        self.stop()

    def has_error(self):
        return False # Simplified for now, relies on logging

    def get_last_error(self):
        return ""

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
            "pitch_estimation": 0.0,
            "pitch_variance": 0.0,
            "speech_rate": 0
            "rms_variance": 0.0,
            "activity_bursts": 0, # Legacy metric kept for backward compatibility
            "speech_rate": 0.0
        }

        if chunk is None or len(chunk) == 0:
            return metrics

        data = chunk.flatten()

        # 1. RMS
        rms = np.sqrt(np.mean(data**2))
        metrics["rms"] = float(rms)

        if rms < 1e-6:
            return metrics

        # 2. Pitch Estimation (FFT)
        try:
            windowed = data * np.hanning(len(data))
            spectrum = np.fft.rfft(windowed)
            frequencies = np.fft.rfftfreq(len(data), 1/self.sample_rate)
            magnitude = np.abs(spectrum)

            magnitude[frequencies < 60] = 0

            peak_idx = np.argmax(magnitude)
            peak_freq = frequencies[peak_idx]
            metrics["pitch_estimation"] = float(peak_freq)

            # 3. Pitch Variance
            sub_chunks = np.array_split(data, 4)
            pitches = []
            for sub in sub_chunks:
                w = sub * np.hanning(len(sub))
                s = np.fft.rfft(w)
                m = np.abs(s)
                f = np.fft.rfftfreq(len(sub), 1/self.sample_rate)
                m[f < 60] = 0
                if np.max(m) > 0.1:
                    p_idx = np.argmax(m)
                    pitches.append(f[p_idx])

            if len(pitches) > 1:
                metrics["pitch_variance"] = float(np.std(pitches))
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
             if self.logger:
                 self.logger.log_event("audio_analysis_error", f"Pitch analysis failed: {e}")

        # 4. Speech Rate (Numpy Peak Detection)
        try:
            abs_signal = np.abs(data)
            window_size = int(0.1 * self.sample_rate)
            envelope = np.convolve(abs_signal, np.ones(window_size)/window_size, mode='same')

            # Numpy Peak Detection
            threshold = rms * 1.2

            mid = envelope[1:-1]
            left = envelope[:-2]
            right = envelope[2:]

            peaks_mask = (mid > left) & (mid > right) & (mid > threshold)

            peak_indices = np.where(peaks_mask)[0] + 1

            if len(peak_indices) > 0:
                filtered_peaks = [peak_indices[0]]
                for idx in peak_indices[1:]:
                    if idx - filtered_peaks[-1] > window_size:
                        filtered_peaks.append(idx)
                metrics["speech_rate"] = len(filtered_peaks)
            else:
                metrics["speech_rate"] = 0

        except Exception as e:
             if self.logger:
                 self.logger.log_event("audio_analysis_error", f"Speech rate analysis failed: {e}")

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
