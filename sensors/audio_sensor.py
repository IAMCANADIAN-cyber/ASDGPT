import sounddevice as sd
import numpy as np
import time
import threading
import queue

class AudioSensor:
    def __init__(self, data_logger=None, logger=None, sample_rate=44100, chunk_duration=1.0, channels=1, history_seconds=5):
        # Support both logger arguments for backward compatibility
        self.logger = data_logger if data_logger else logger
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

    def analyze_chunk(self, chunk):
        metrics = {
            "rms": 0.0,
            "pitch_estimation": 0.0,
            "pitch_variance": 0.0,
            "speech_rate": 0
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
