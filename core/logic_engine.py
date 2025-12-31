import time
import config
import threading
from typing import Optional, Callable, Any
import numpy as np
import cv2
import base64
from .data_logger import DataLogger
from .lmm_interface import LMMInterface
from .intervention_engine import InterventionEngine


class LogicEngine:
    def __init__(self, audio_sensor: Optional[Any] = None, video_sensor: Optional[Any] = None, logger: Optional[DataLogger] = None, lmm_interface: Optional[LMMInterface] = None) -> None:
        self.current_mode: str = config.DEFAULT_MODE
        self.snooze_end_time: float = 0
        self.previous_mode_before_pause: str = config.DEFAULT_MODE
        self.tray_callback: Optional[Callable[[str, Optional[str]], None]] = None
        self.audio_sensor: Optional[Any] = audio_sensor
        self.video_sensor: Optional[Any] = video_sensor
        self.logger: DataLogger = logger if logger else DataLogger()
        self.lmm_interface: Optional[LMMInterface] = lmm_interface
        self.intervention_engine: Optional[InterventionEngine] = None
        self._lock: threading.Lock = threading.Lock()

        # Sensor data storage
        self.last_video_frame: Optional[np.ndarray] = None
        self.previous_video_frame: Optional[np.ndarray] = None
        self.last_audio_chunk: Optional[np.ndarray] = None

        # Sensor metrics
        self.audio_level: float = 0.0
        self.video_activity: float = 0.0

        # LMM trigger logic
        self.last_lmm_call_time: float = 0
        self.lmm_call_interval: int = 5  # Periodic check interval (seconds)
        self.min_lmm_interval: int = 2   # Minimum time between calls even for triggers (seconds)

        # Thresholds (could be moved to config later)
        self.audio_threshold_high = 0.5 # Example normalized threshold
        self.video_activity_threshold_high = 20.0 # Example pixel diff threshold

        self.logger.log_info(f"LogicEngine initialized. Mode: {self.current_mode}")

    def get_mode(self) -> str:
        with self._lock:
            return self.current_mode

    def set_mode(self, mode: str, from_snooze_expiry: bool = False) -> None:
        with self._lock:
            self._set_mode_unlocked(mode, from_snooze_expiry)

    def _set_mode_unlocked(self, mode: str, from_snooze_expiry: bool = False) -> None:
        if mode not in ["active", "snoozed", "paused", "error"]:
            self.logger.log_warning(f"Attempted to set invalid mode: {mode}")
            return

        old_mode = self.current_mode
        if mode == old_mode and not from_snooze_expiry:
            if not (mode == "active" and from_snooze_expiry and old_mode == "snoozed"):
                return

        self.logger.log_info(f"LogicEngine: Changing mode from {old_mode} to {mode}")

        if old_mode != "paused" and mode == "paused":
            self.previous_mode_before_pause = old_mode

        self.current_mode = mode

        if self.current_mode == "snoozed":
            self.snooze_end_time = time.time() + config.SNOOZE_DURATION
            self.logger.log_info(f"Snooze activated. Will return to active mode in {config.SNOOZE_DURATION / 60:.0f} minutes.")
        elif self.current_mode == "active":
            self.snooze_end_time = 0

        self._notify_mode_change(old_mode, new_mode=self.current_mode, from_snooze_expiry=from_snooze_expiry)

    def cycle_mode(self) -> None:
        with self._lock:
            current_actual_mode = self.get_mode()
            if current_actual_mode == "active":
                self._set_mode_unlocked("snoozed")
            elif current_actual_mode == "snoozed":
                self._set_mode_unlocked("paused")
            elif current_actual_mode == "paused":
                self._set_mode_unlocked("active")

    def toggle_pause_resume(self) -> None:
        with self._lock:
            current_actual_mode = self.get_mode()
            if current_actual_mode == "paused":
                if self.previous_mode_before_pause == "snoozed" and \
                   self.snooze_end_time != 0 and time.time() >= self.snooze_end_time:
                    self.snooze_end_time = 0
                    self._set_mode_unlocked("active")
                else:
                    self._set_mode_unlocked(self.previous_mode_before_pause)
            else:
                self._set_mode_unlocked("paused")

    def set_intervention_engine(self, intervention_engine: InterventionEngine) -> None:
        """Sets the intervention engine for the logic engine to use."""
        self.intervention_engine = intervention_engine

    def _notify_mode_change(self, old_mode: str, new_mode: str, from_snooze_expiry: bool = False) -> None:
        self.logger.log_info(f"LogicEngine Notification: Mode changed from {old_mode} to {new_mode}{' (due to snooze expiry)' if from_snooze_expiry else ''}")
        if self.tray_callback:
            self.tray_callback(new_mode=new_mode, old_mode=old_mode)

    def process_video_data(self, frame: np.ndarray) -> None:
        with self._lock:
            self.previous_video_frame = self.last_video_frame
            self.last_video_frame = frame

            # Calculate video activity (motion)
            if self.previous_video_frame is not None and self.last_video_frame is not None:
                # Ensure shapes match before diffing
                if self.previous_video_frame.shape == self.last_video_frame.shape:
                    diff = cv2.absdiff(self.previous_video_frame, self.last_video_frame)
                    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                    self.video_activity = np.mean(gray_diff)
                else:
                    self.video_activity = 0.0 # Reset if shapes mismatch (e.g. cam change)
            else:
                self.video_activity = 0.0

        self.logger.log_debug(f"Processed video frame. Activity: {self.video_activity:.2f}")

    def process_audio_data(self, audio_chunk: np.ndarray) -> None:
        with self._lock:
            self.last_audio_chunk = audio_chunk

            # Calculate audio level (RMS)
            if len(audio_chunk) > 0:
                self.audio_level = np.sqrt(np.mean(audio_chunk**2))
            else:
                self.audio_level = 0.0

        self.logger.log_debug(f"Processed audio chunk. Level: {self.audio_level:.4f}")

    def _prepare_lmm_data(self, trigger_reason: str = "periodic") -> Optional[dict]:
        with self._lock:
            if self.last_video_frame is None and self.last_audio_chunk is None:
                return None

            video_data_b64 = None
            if self.last_video_frame is not None:
                try:
                    # Compress to reduce payload size
                    _, buffer = cv2.imencode('.jpg', self.last_video_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    video_data_b64 = base64.b64encode(buffer).decode('utf-8')
                except Exception as e:
                     self.logger.log_warning(f"Error encoding video frame: {e}")

            audio_data_list = None
            if self.last_audio_chunk is not None:
                # Downsample or limit audio data size if needed for LMM
                # For now, sending raw list
                audio_data_list = self.last_audio_chunk.tolist()

            # Note: We are NOT clearing self.last_video_frame here to allow subsequent checks,
            # but usually we want fresh data.
            # If we clear it, we might lose context if the LMM call fails and we retry.
            # However, standard practice here is to send snapshot.

            context = {
                "current_mode": self.current_mode,
                "trigger_reason": trigger_reason,
                "sensor_metrics": {
                    "audio_level": float(self.audio_level),
                    "video_activity": float(self.video_activity)
                }
            }

            return {
                "video_data": video_data_b64,
                "audio_data": audio_data_list,
                "user_context": context
            }

    def _trigger_lmm_analysis(self, reason: str) -> None:
    def _trigger_lmm_analysis(self, allow_intervention: bool = True) -> None:
        if not self.lmm_interface:
            self.logger.log_warning("LMM interface not available.")
            return

        lmm_payload = self._prepare_lmm_data(trigger_reason=reason)
        if not lmm_payload:
            self.logger.log_debug("No new sensor data to send to LMM.")
            return

        self.logger.log_info(f"Triggering LMM analysis (Reason: {reason})...")

        # We can run this in a separate thread if process_data is blocking and slow,
        # but for now we keep it simple as LogicEngine.update is called from main loop.
        # If LMM call is slow, it might block the main loop (GUI/Sensors).
        # Ideally, LMM interface should be async or threaded.
        # For this implementation, we assume LMMInterface handles it or we accept the delay.

        analysis = self.lmm_interface.process_data(
            video_data=lmm_payload["video_data"],
            audio_data=lmm_payload["audio_data"],
            user_context=lmm_payload["user_context"]
        )

        if analysis and self.intervention_engine:
            suggestion = self.lmm_interface.get_intervention_suggestion(analysis)
            if suggestion:
                if allow_intervention:
                    self.logger.log_info(f"LMM suggested intervention: {suggestion}")
                    self.intervention_engine.start_intervention(suggestion)
                else:
                    self.logger.log_info(f"LMM suggested intervention (suppressed due to mode): {suggestion}")

    def update(self) -> None:
        """
        Periodically called to update the logic engine's state and evaluations.
        Implements the main active mode logic loop.
        """
        with self._lock:
            # 0. Check snooze expiry
            if self.current_mode == "snoozed" and self.snooze_end_time != 0 and time.time() >= self.snooze_end_time:
                self.logger.log_info("Snooze expired.")
                self.snooze_end_time = 0
                self._set_mode_unlocked("active", from_snooze_expiry=True)

        current_mode = self.get_mode()
        # self.logger.log_debug(f"LogicEngine update. Current mode: {current_mode}")

        if current_mode == "active":
            current_time = time.time()
            trigger_lmm = False
            trigger_reason = ""

            # 1. Process sensor data & Evaluate conditions (Metrics updated in process_* methods)
            # We access metrics (atomic reads roughly safe, but better with lock if precise)
            # Using local copies for decision making
            with self._lock:
                current_audio_level = self.audio_level
                current_video_activity = self.video_activity

            # 2. Check for Event-based Triggers
            # Check for sudden loud noise
            if current_audio_level > self.audio_threshold_high:
                if current_time - self.last_lmm_call_time >= self.min_lmm_interval:
                    trigger_lmm = True
                    trigger_reason = "high_audio_level"

            # Check for high activity (or sudden movement)
            elif current_video_activity > self.video_activity_threshold_high:
                if current_time - self.last_lmm_call_time >= self.min_lmm_interval:
                    trigger_lmm = True
                    trigger_reason = "high_video_activity"

            # 3. Periodic Check (Heartbeat)
            # If no event triggered, check if it's time for a routine check
            if not trigger_lmm:
                if current_time - self.last_lmm_call_time >= self.lmm_call_interval:
                    trigger_lmm = True
                    trigger_reason = "periodic_check"

            # 4. Trigger LMM if warranted
            if trigger_lmm:
                self.last_lmm_call_time = current_time
                self._trigger_lmm_analysis(reason=trigger_reason)

            # 5. Potentially change mode (e.g. error)
            # (Note: Main application handles sensor hardware errors.
            # LogicEngine could handle logical errors, e.g., if we consistently get black frames
            # but no hardware error is reported. For now, we leave that to future expansion.)
                self._trigger_lmm_analysis(allow_intervention=True)
        elif current_mode == "snoozed":
            self.logger.log_debug("LogicEngine: Mode is SNOOZED. Performing light monitoring without intervention.")
            current_time = time.time()
            if current_time - self.last_lmm_call_time >= self.lmm_call_interval:
                self.last_lmm_call_time = current_time
                self._trigger_lmm_analysis(allow_intervention=False)


if __name__ == '__main__':
    # Mock sensor classes for testing
    class MockSensor:
        def __init__(self, name="mock"):
            self.name = name

    class MockLMMInterface:
        def __init__(self):
            self.last_call_data = None
        def process_data(self, video_data=None, audio_data=None, user_context=None):
            self.last_call_data = {
                "video_data": "present" if video_data else None,
                "audio_data": "present" if audio_data else None,
                "user_context": user_context
            }
            print(f"MockLMMInterface process_data called. Reason: {user_context.get('trigger_reason')}")
            return {"suggestion": {"type": "test_intervention", "message": "Test"}}

        def get_intervention_suggestion(self, analysis):
            return analysis.get("suggestion")

    class MockInterventionEngine:
        def start_intervention(self, suggestion):
            print(f"MockInterventionEngine: Starting {suggestion}")

    mock_lmm = MockLMMInterface()
    mock_intervention = MockInterventionEngine()

    # Setup Logger
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "test_logic_engine_log.txt"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"
    logger = DataLogger(log_file_path=config.LOG_FILE)

    engine = LogicEngine(logger=logger, lmm_interface=mock_lmm)
    engine.set_intervention_engine(mock_intervention)

    # Adjust thresholds for testing
    engine.lmm_call_interval = 2
    engine.min_lmm_interval = 0 # Allow immediate calls for test
    engine.audio_threshold_high = 0.5
    engine.video_activity_threshold_high = 10.0

    print("--- Testing LogicEngine Active Mode Logic ---")

    # Test 1: Periodic Check
    print("\nTest 1: Periodic Check (No data initially)")
    engine.update() # Should trigger periodic because last_call_time is 0
    assert mock_lmm.last_call_data is None # No data prepared, so no call actually goes out (log says "No new sensor data")

    # Feed some data
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    engine.process_video_data(frame1)
    engine.process_audio_data(np.zeros(1024))

    # Reset timer for controlled test
    engine.last_lmm_call_time = time.time() - 5
    engine.update()
    assert mock_lmm.last_call_data is not None
    assert mock_lmm.last_call_data["user_context"]["trigger_reason"] == "periodic_check"
    print("Periodic check passed.")

    # Test 2: High Audio Trigger
    print("\nTest 2: High Audio Trigger")
    engine.last_lmm_call_time = time.time() # Reset timer, so periodic won't fire

    # Simulate loud audio
    loud_audio = np.ones(1024) * 0.8
    engine.process_audio_data(loud_audio)

    engine.update()
    assert mock_lmm.last_call_data["user_context"]["trigger_reason"] == "high_audio_level"
    assert mock_lmm.last_call_data["user_context"]["sensor_metrics"]["audio_level"] > 0.5
    print("High audio trigger passed.")

    # Test 3: High Video Activity Trigger
    print("\nTest 3: High Video Activity Trigger")
    engine.last_lmm_call_time = time.time() # Reset timer

    # Reset audio to silence so it doesn't trigger audio threshold again
    silence = np.zeros(1024)
    engine.process_audio_data(silence)

    # Current frame is black (from Test 1). Send white frame to cause high diff
    white_frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
    engine.process_video_data(white_frame)

    engine.update()
    assert mock_lmm.last_call_data["user_context"]["trigger_reason"] == "high_video_activity"
    assert mock_lmm.last_call_data["user_context"]["sensor_metrics"]["video_activity"] > 10.0
    print("High video activity trigger passed.")

    print("\nLogicEngine tests complete.")
