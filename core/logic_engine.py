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
from .state_engine import StateEngine


class LogicEngine:
    def __init__(self, audio_sensor: Optional[Any] = None, video_sensor: Optional[Any] = None, logger: Optional[DataLogger] = None, lmm_interface: Optional[LMMInterface] = None) -> None:
        self.current_mode: str = config.DEFAULT_MODE
        self.snooze_end_time: float = 0
        self.previous_mode_before_pause: str = config.DEFAULT_MODE
        self.tray_callback: Optional[Callable[[str, Optional[str]], None]] = None
        self.state_update_callback: Optional[Callable[[dict], None]] = None
        self.notification_callback: Optional[Callable[[str, str], None]] = None
        self.audio_sensor: Optional[Any] = audio_sensor
        self.video_sensor: Optional[Any] = video_sensor
        self.logger: DataLogger = logger if logger else DataLogger()
        self.lmm_interface: Optional[LMMInterface] = lmm_interface
        self.intervention_engine: Optional[InterventionEngine] = None
        self.state_engine: StateEngine = StateEngine(logger=self.logger)
        self._lock: threading.Lock = threading.Lock()

        # Async LMM handling
        self.lmm_thread: Optional[threading.Thread] = None

        # Sensor data storage
        self.last_video_frame: Optional[np.ndarray] = None
        self.previous_video_frame: Optional[np.ndarray] = None
        self.last_audio_chunk: Optional[np.ndarray] = None

        # Sensor metrics
        self.audio_level: float = 0.0
        self.video_activity: float = 0.0
        self.face_metrics: dict = {"face_detected": False, "face_count": 0}
        self.video_analysis: dict = {}
        self.audio_analysis: dict = {}

        # LMM trigger logic
        self.last_lmm_call_time: float = 0
        self.lmm_call_interval: int = 5  # Periodic check interval (seconds)
        self.min_lmm_interval: int = 2   # Minimum time between calls even for triggers (seconds)

        # Thresholds
        # Thresholds (loaded from config)
        self.audio_threshold_high = config.AUDIO_THRESHOLD_HIGH
        self.video_activity_threshold_high = config.VIDEO_ACTIVITY_THRESHOLD_HIGH

        # Error recovery
        self.error_recovery_attempts: int = 0
        self.max_error_recovery_attempts: int = 3
        self.last_error_log_time: float = 0
        self.error_recovery_interval: int = 5 # seconds
        self.last_error_recovery_attempt_time: float = 0
        self.recovery_probation_end_time: float = 0
        self.recovery_probation_duration: int = 10 # seconds

        # LMM Circuit Breaker
        self.lmm_consecutive_failures: int = 0
        self.lmm_circuit_breaker_open_until: float = 0

        # Context Persistence (for specialized triggers like Doom Scrolling)
        self.context_persistence: dict = {} # Stores counts of consecutive tags e.g. {"phone_usage": 0}
        self.doom_scroll_trigger_threshold: int = getattr(config, 'DOOM_SCROLL_THRESHOLD', 3)

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

        if mode == "active" and old_mode == "error":
             self.logger.log_info("Entered active mode from error. Starting probation period.")
             self.recovery_probation_end_time = time.time() + self.recovery_probation_duration
             # Do not reset attempts yet.

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

            # Use VideoSensor's unified processing if available
            if self.video_sensor and hasattr(self.video_sensor, 'process_frame'):
                metrics = self.video_sensor.process_frame(frame)
                self.video_activity = metrics.get("video_activity", 0.0)

                # Filter out non-face metrics for face_metrics dict
                self.face_metrics = {k: v for k, v in metrics.items() if k.startswith("face_")}
                self.video_analysis = self.face_metrics # Reuse for analysis context

            else:
                # Fallback to legacy calculation (if sensor doesn't have process_frame or is missing)
                if self.previous_video_frame is not None and self.last_video_frame is not None:
                    # Ensure shapes match before diffing
                    if self.previous_video_frame.shape == self.last_video_frame.shape:
                        diff = cv2.absdiff(self.previous_video_frame, self.last_video_frame)
                        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                        self.video_activity = np.mean(gray_diff)
                    else:
                        self.video_activity = 0.0
                else:
                    self.video_activity = 0.0

                self.face_metrics = {"face_detected": False, "face_count": 0}
                self.video_analysis = {}

        self.logger.log_debug(f"Processed video frame. Activity: {self.video_activity:.2f}, Face: {self.face_metrics.get('face_detected')}")

    def process_audio_data(self, audio_chunk: np.ndarray) -> None:
        with self._lock:
            self.last_audio_chunk = audio_chunk

            # Use AudioSensor analysis if available
            if self.audio_sensor and hasattr(self.audio_sensor, 'analyze_chunk'):
                self.audio_analysis = self.audio_sensor.analyze_chunk(audio_chunk)
                self.audio_level = self.audio_analysis.get('rms', 0.0)
            else:
                # Fallback calculation
                if len(audio_chunk) > 0:
                    self.audio_level = np.sqrt(np.mean(audio_chunk**2))
                else:
                    self.audio_level = 0.0
                self.audio_analysis = {"rms": self.audio_level}

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

            # Fetch suppressed interventions if available
            suppressed_list = []
            preferred_list = []
            if self.intervention_engine:
                if hasattr(self.intervention_engine, 'get_suppressed_intervention_types'):
                    suppressed_list = self.intervention_engine.get_suppressed_intervention_types()
                if hasattr(self.intervention_engine, 'get_preferred_intervention_types'):
                    preferred_list = self.intervention_engine.get_preferred_intervention_types()

            # Generate System Alerts based on persistence
            system_alerts = []
            if self.context_persistence.get("phone_usage", 0) >= self.doom_scroll_trigger_threshold:
                 system_alerts.append("Persistent Phone Usage Detected (Potential Doom Scrolling)")

            context = {
                "current_mode": self.current_mode,
                "trigger_reason": trigger_reason,
                "sensor_metrics": {
                    "audio_level": float(self.audio_level),
                    "video_activity": float(self.video_activity),
                    "face_detected": bool(self.face_metrics.get("face_detected", False)),
                    "face_count": int(self.face_metrics.get("face_count", 0)),
                    "video_analysis": self.video_analysis,
                    "audio_analysis": self.audio_analysis
                },
                "current_state_estimation": self.state_engine.get_state(),
                "suppressed_interventions": suppressed_list,
                "system_alerts": system_alerts,
                "preferred_interventions": preferred_list
            }

            return {
                "video_data": video_data_b64,
                "audio_data": audio_data_list,
                "user_context": context
            }

    def _run_lmm_analysis_async(self, lmm_payload: dict, allow_intervention: bool) -> None:
        """Background worker for LMM analysis."""
        try:
            analysis = self.lmm_interface.process_data(
                video_data=lmm_payload["video_data"],
                audio_data=lmm_payload["audio_data"],
                user_context=lmm_payload["user_context"]
            )

            if analysis:
                # Reset circuit breaker on success (even if it's a fallback, though ideally fallback shouldn't count as 'network success'
                # but LMMInterface handles that. LMMInterface returns fallback if network failed.
                # If we get a response, the interface handled it.
                # If analysis has _meta.is_fallback, it means LMM failed.

                is_fallback = analysis.get("_meta", {}).get("is_fallback", False)
                if is_fallback:
                    self.lmm_consecutive_failures += 1
                    self.logger.log_warning(f"LMM returned fallback response. Consecutive failures: {self.lmm_consecutive_failures}")

                    if self.lmm_consecutive_failures >= config.LMM_CIRCUIT_BREAKER_MAX_FAILURES:
                         self.lmm_circuit_breaker_open_until = time.time() + config.LMM_CIRCUIT_BREAKER_COOLDOWN
                         self.logger.log_error(f"LMM Circuit Breaker OPENED. Pausing LMM calls for {config.LMM_CIRCUIT_BREAKER_COOLDOWN}s.")
                else:
                    if self.lmm_consecutive_failures > 0:
                        self.logger.log_info("LMM recovered. Resetting failure count.")
                    self.lmm_consecutive_failures = 0
                # Check if it was a fallback response
                if analysis.get("fallback"):
                     self.logger.log_warning("LMM analysis used fallback mechanism.")

                # Update state estimation (StateEngine should be thread-safe or we assume simple updates)
                self.state_engine.update(analysis)
                self.logger.log_info("LMM analysis complete and state updated.")

                # Process Visual Context
                reflexive_intervention_id = None
                visual_context = analysis.get("visual_context", [])
                triggered_intervention_id = None
                if visual_context:
                    self.logger.log_info(f"LMM Detected Visual Context: {visual_context}")
                    triggered_intervention_id = self._process_visual_context_triggers(visual_context)
                    reflexive_intervention_id = triggered_intervention_id # Alias for below logic if needed

                # Log state update event
                self.logger.log_event("state_update", self.state_engine.get_state())

                # Update tray tooltip with new state
                if hasattr(self, 'state_update_callback') and self.state_update_callback:
                    self.state_update_callback(self.state_engine.get_state())

            else:
                 # LogicEngine received None (hard failure in interface even after retries and no fallback?)
                 # This usually means no fallback was enabled or interface crashed.
                 self.lmm_consecutive_failures += 1
                 if self.lmm_consecutive_failures >= config.LMM_CIRCUIT_BREAKER_MAX_FAILURES:
                     self.lmm_circuit_breaker_open_until = time.time() + config.LMM_CIRCUIT_BREAKER_COOLDOWN
                     self.logger.log_error(f"LMM Circuit Breaker OPENED (No Response). Pausing LMM calls for {config.LMM_CIRCUIT_BREAKER_COOLDOWN}s.")
                 triggered_intervention_id = None # Ensure defined in this scope


            if analysis and self.intervention_engine:
                suggestion = self.lmm_interface.get_intervention_suggestion(analysis)

                # Reflexive triggers take priority over lack of suggestion,
                # OR can override if needed (policy decision).
                # For now: if LMM suggests nothing (or None), but we have a reflexive trigger, use it.
                if not suggestion and reflexive_intervention_id:
                     self.logger.log_info(f"Reflexive Trigger activated: {reflexive_intervention_id}")
                     suggestion = {"id": reflexive_intervention_id}

                if suggestion:
                    # Priority: System Triggers > LMM Suggestion
                    final_intervention = None

                if triggered_intervention_id:
                    final_intervention = {"id": triggered_intervention_id}
                    self.logger.log_info(f"System Trigger overrides LMM suggestion. Triggered: {triggered_intervention_id}")
                elif suggestion:
                    final_intervention = suggestion

                if final_intervention:
                    if allow_intervention:
                        self.logger.log_info(f"Starting intervention: {final_intervention}")
                        # start_intervention is generally thread-safe as it just sets an event/launches another thread
                        self.intervention_engine.start_intervention(final_intervention)
                    else:
                        self.logger.log_info(f"Intervention suggested but suppressed due to mode: {final_intervention}")
        except Exception as e:
            self.logger.log_error(f"Error in async LMM analysis: {e}")
            self.lmm_consecutive_failures += 1

    def _process_visual_context_triggers(self, visual_context: list) -> Optional[str]:
        """
        Analyzes visual context tags for persistent patterns (e.g., Doom Scrolling).
        Returns an intervention ID string if a specific persistent trigger is met, else None.
        Returns an intervention ID if a trigger condition is met, else None.
        """
        # Tags we track for persistence
        tracked_tags = ["phone_usage", "messy_room"]

        for tag in tracked_tags:
            if tag in visual_context:
                self.context_persistence[tag] = self.context_persistence.get(tag, 0) + 1
            else:
                self.context_persistence[tag] = 0

        # Check for Doom Scroll Trigger
        if self.context_persistence.get("phone_usage", 0) >= self.doom_scroll_trigger_threshold:
            self.logger.log_info("LogicEngine: 'Doom Scroll' persistence threshold reached!")
            return "doom_scroll_breaker"

        return None

    def _trigger_lmm_analysis(self, reason: str = "unknown", allow_intervention: bool = True) -> None:
        if not self.lmm_interface:
            self.logger.log_warning("LMM interface not available.")
            return

        # Check Circuit Breaker
        if time.time() < self.lmm_circuit_breaker_open_until:
             self.logger.log_debug(f"Skipping LMM trigger ({reason}): Circuit breaker is OPEN.")
             return

        # Check if previous analysis is still running
        if self.lmm_thread and self.lmm_thread.is_alive():
            self.logger.log_info(f"Skipping LMM trigger ({reason}): Previous analysis still running.")
            return

        lmm_payload = self._prepare_lmm_data(trigger_reason=reason)
        if not lmm_payload:
            self.logger.log_debug("No new sensor data to send to LMM.")
            return

        self.logger.log_info(f"Triggering LMM analysis (Reason: {reason})...")
        self.logger.log_event("lmm_trigger", {"reason": reason})

        # Run in background thread to avoid blocking main loop
        self.lmm_thread = threading.Thread(
            target=self._run_lmm_analysis_async,
            args=(lmm_payload, allow_intervention),
            daemon=True
        )
        self.lmm_thread.start()

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

            # Check probation
            if self.recovery_probation_end_time > 0 and current_time > self.recovery_probation_end_time:
                self.logger.log_info("Error recovery probation passed. Resetting error counters.")
                self.error_recovery_attempts = 0
                self.recovery_probation_end_time = 0

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

        elif current_mode == "error":
            current_time = time.time()
            if current_time - self.last_error_log_time > 10:
                self.logger.log_debug("LogicEngine: Mode is ERROR. Attempting to handle or log.")
                self.last_error_log_time = current_time

            # 1. Log detailed error information (handled by setting mode and callers, but we ensure state is known)
            # 2. Attempt recovery if possible.
            if self.error_recovery_attempts < self.max_error_recovery_attempts:
                if current_time - self.last_error_recovery_attempt_time > self.error_recovery_interval:
                    self.logger.log_info(f"Attempting error recovery ({self.error_recovery_attempts + 1}/{self.max_error_recovery_attempts})...")
                    self.last_error_recovery_attempt_time = current_time
                    self.error_recovery_attempts += 1

                    # Attempt to revert to previous known good state or default active
                    target_mode = self.previous_mode_before_pause if self.previous_mode_before_pause != "error" else "active"
                    self.logger.log_info(f"Resetting mode to {target_mode} for recovery check.")

                    # We use set_mode. If the underlying cause (e.g. sensor error) persists,
                    # main.py or sensor checks will likely set it back to error shortly.
                    self.set_mode(target_mode)

            # 3. Notify user of persistent error state.
            elif self.error_recovery_attempts == self.max_error_recovery_attempts:
                self.logger.log_error("Max error recovery attempts reached. User intervention required.")
                if self.notification_callback:
                    self.notification_callback("System Error", "The system has encountered a persistent error and could not recover automatically. Please check logs.")
                self.error_recovery_attempts += 1 # Increment once more to stop notifying repeatedly

        elif current_mode == "snoozed":
            self.logger.log_debug("LogicEngine: Mode is SNOOZED. Performing light monitoring without intervention.")
            current_time = time.time()
            if current_time - self.last_lmm_call_time >= self.lmm_call_interval:
                self.last_lmm_call_time = current_time
                self._trigger_lmm_analysis(allow_intervention=False)

    def shutdown(self) -> None:
        """
        Gracefully shuts down the LogicEngine, ensuring background threads complete.
        """
        self.logger.log_info("LogicEngine shutting down...")
        if self.lmm_thread and self.lmm_thread.is_alive():
            self.logger.log_info("Waiting for LMM analysis thread to finish...")
            self.lmm_thread.join(timeout=5.0)
            if self.lmm_thread.is_alive():
                self.logger.log_warning("LMM analysis thread did not finish in time.")
            else:
                self.logger.log_info("LMM analysis thread finished.")


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
            return {
                "suggestion": {"type": "test_intervention", "message": "Test"},
                "state_estimation": {"arousal": 55, "overload": 10, "focus": 60, "energy": 75, "mood": 55}
            }

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
    # Wait for async thread if any (should generally be none here as no data)
    if engine.lmm_thread: engine.lmm_thread.join()
    assert mock_lmm.last_call_data is None # No data prepared, so no call actually goes out (log says "No new sensor data")

    # Feed some data
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    engine.process_video_data(frame1)
    engine.process_audio_data(np.zeros(1024))

    # Reset timer for controlled test
    engine.last_lmm_call_time = time.time() - 5
    engine.update()

    # Wait for async thread to complete
    if engine.lmm_thread: engine.lmm_thread.join()

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

    # Wait for async thread to complete
    if engine.lmm_thread: engine.lmm_thread.join()

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

    # Wait for async thread to complete
    if engine.lmm_thread: engine.lmm_thread.join()

    assert mock_lmm.last_call_data["user_context"]["trigger_reason"] == "high_video_activity"
    assert mock_lmm.last_call_data["user_context"]["sensor_metrics"]["video_activity"] > 10.0
    print("High video activity trigger passed.")

    print("\nLogicEngine tests complete.")
