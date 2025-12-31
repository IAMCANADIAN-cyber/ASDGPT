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

        self.last_video_frame: Optional[np.ndarray] = None
        self.last_audio_chunk: Optional[np.ndarray] = None
        self.last_lmm_call_time: float = 0
        self.lmm_call_interval: int = 5  # seconds

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
            self.last_video_frame = frame
        self.logger.log_debug(f"Stored latest video frame of shape {frame.shape}")

    def process_audio_data(self, audio_chunk: np.ndarray) -> None:
        with self._lock:
            self.last_audio_chunk = audio_chunk
        self.logger.log_debug(f"Stored latest audio chunk of shape {audio_chunk.shape}")

    def _prepare_lmm_data(self) -> Optional[dict]:
        with self._lock:
            if self.last_video_frame is None and self.last_audio_chunk is None:
                return None

            video_data_b64 = None
            if self.last_video_frame is not None:
                _, buffer = cv2.imencode('.jpg', self.last_video_frame)
                video_data_b64 = base64.b64encode(buffer).decode('utf-8')

            audio_data_list = None
            if self.last_audio_chunk is not None:
                audio_data_list = self.last_audio_chunk.tolist()

            # Clear the data after preparing it
            self.last_video_frame = None
            self.last_audio_chunk = None

            return {
                "video_data": video_data_b64,
                "audio_data": audio_data_list,
                "user_context": {"current_mode": self.current_mode}
            }

    def _trigger_lmm_analysis(self, allow_intervention: bool = True) -> None:
        if not self.lmm_interface:
            self.logger.log_warning("LMM interface not available.")
            return

        lmm_payload = self._prepare_lmm_data()
        if not lmm_payload:
            self.logger.log_debug("No new sensor data to send to LMM.")
            return

        self.logger.log_info("Sending data to LMM...")
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
        For now, primarily ensures snooze expiry is checked.
        """
        with self._lock:
            if self.current_mode == "snoozed" and time.time() >= self.snooze_end_time and self.snooze_end_time != 0:
                self.logger.log_info("Snooze expired.")
                self.snooze_end_time = 0
                self._set_mode_unlocked("active", from_snooze_expiry=True)

        current_mode = self.get_mode()
        self.logger.log_debug(f"LogicEngine update. Current mode: {current_mode}")

        if current_mode == "active":
            current_time = time.time()
            if current_time - self.last_lmm_call_time >= self.lmm_call_interval:
                self.last_lmm_call_time = current_time
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
        def get_level(self):
            return f"{self.name}_level_data"
        def get_activity_level(self):
            return f"{self.name}_activity_data"

    class MockLMMInterface:
        def __init__(self):
            self.last_call_data = None
        def process_data(self, video_data=None, audio_data=None, user_context=None):
            self.last_call_data = {
                "video_data": video_data,
                "audio_data": audio_data,
                "user_context": user_context
            }
            print(f"MockLMMInterface process_data called with: {self.last_call_data}")

    mock_audio = MockSensor("audio")
    mock_video = MockSensor("video")
    mock_lmm = MockLMMInterface()

    # Assuming DataLogger is in the same directory or properly pathed
    # For testing, let's ensure config has defaults if not present
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "test_logic_engine_log.txt"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"

    logger = DataLogger(log_file_path=config.LOG_FILE) # Use a specific logger for the test output

    engine = LogicEngine(audio_sensor=mock_audio, video_sensor=mock_video, logger=logger, lmm_interface=mock_lmm)
    engine.lmm_call_interval = 0  # Force immediate LMM calls for testing

    # Mock callback for testing
    def test_callback(new_mode, old_mode):
        print(f"Test Callback: Mode changed from {old_mode} to {new_mode}")
    engine.tray_callback = test_callback

    print("--- Testing LMMInterface integration ---")
    print("\n--- Test Case: process_video_data and update ---")
    test_frame = np.zeros((480, 640, 3))
    engine.process_video_data(test_frame)
    engine.update() # This should trigger the LMM call
    assert mock_lmm.last_call_data is not None
    assert mock_lmm.last_call_data["video_data"] is not None
    assert mock_lmm.last_call_data["audio_data"] is None
    assert mock_lmm.last_call_data["user_context"] is not None

    print("\n--- Test Case: process_audio_data and update ---")
    test_chunk = np.zeros(1024)
    engine.process_audio_data(test_chunk)
    engine.update() # This should trigger the LMM call
    assert mock_lmm.last_call_data is not None
    assert mock_lmm.last_call_data["video_data"] is None
    assert mock_lmm.last_call_data["audio_data"] is not None
    assert mock_lmm.last_call_data["user_context"] is not None
    print("LogicEngine LMM integration tests complete.")
