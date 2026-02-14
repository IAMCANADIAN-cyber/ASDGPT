import time
import config
import threading
from collections import deque
from typing import Optional, Callable, Any
import numpy as np
import cv2
import base64
from .data_logger import DataLogger
from .lmm_interface import LMMInterface
from .intervention_engine import InterventionEngine
from .state_engine import StateEngine
from .stt_interface import STTInterface
from .music_interface import MusicInterface


class LogicEngine:
    def __init__(self, audio_sensor: Optional[Any] = None, video_sensor: Optional[Any] = None, window_sensor: Optional[Any] = None, logger: Optional[DataLogger] = None, lmm_interface: Optional[LMMInterface] = None) -> None:
        self.current_mode: str = config.DEFAULT_MODE
        self.snooze_end_time: float = 0
        self.previous_mode_before_pause: str = config.DEFAULT_MODE
        self.tray_callback: Optional[Callable[[str, Optional[str]], None]] = None
        self.state_update_callback: Optional[Callable[[dict], None]] = None
        self.notification_callback: Optional[Callable[[str, str], None]] = None
        self.audio_sensor: Optional[Any] = audio_sensor
        self.video_sensor: Optional[Any] = video_sensor
        self.window_sensor: Optional[Any] = window_sensor
        self.logger: DataLogger = logger if logger else DataLogger()
        self.lmm_interface: Optional[LMMInterface] = lmm_interface
        self.intervention_engine: Optional[InterventionEngine] = None
        self.state_engine: StateEngine = StateEngine(logger=self.logger)
        self.stt_interface: STTInterface = STTInterface(logger=self.logger)
        self.music_interface: MusicInterface = MusicInterface(logger=self.logger)
        self._lock: threading.Lock = threading.Lock()

        # Async LMM handling
        self.lmm_thread: Optional[threading.Thread] = None
        self.stt_thread: Optional[threading.Thread] = None

        # Sensor data storage
        self.last_video_frame: Optional[np.ndarray] = None
        self.previous_video_frame: Optional[np.ndarray] = None
        self.last_audio_chunk: Optional[np.ndarray] = None
        self.audio_buffer_for_stt: deque = deque(maxlen=int(44100 * 30)) # 30 sec max buffer
        self.last_speech_state: bool = False
        self.speech_start_time: float = 0
        self.last_transcription: Optional[str] = None
        self.last_transcription_time: float = 0

        # Sensor metrics
        self.audio_level: float = 0.0
        self.video_activity: float = 0.0
        self.face_metrics: dict = {"face_detected": False, "face_count": 0}
        self.video_analysis: dict = {}
        self.audio_analysis: dict = {}

        # LMM trigger logic
        self.last_lmm_call_time: float = 0

        # Adjust intervals based on performance mode
        perf_mode = getattr(config, 'PERFORMANCE_MODE', 'high')
        if perf_mode == 'low':
            self.lmm_call_interval: int = 10
            self.min_lmm_interval: int = 5
        else:
            self.lmm_call_interval: int = 5
            self.min_lmm_interval: int = 2

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

        # Offline Fallback
        self.last_offline_trigger_time: float = 0
        self.offline_trigger_interval: int = 30 # Seconds between offline interventions

        # Meeting Mode Heuristics
        self.last_user_input_time: float = time.time()
        self.input_tracking_enabled: bool = False
        self.continuous_speech_start_time: float = 0
        self.auto_dnd_active: bool = False
        self.last_speech_time: float = 0

        # Context Persistence (for specialized triggers like Doom Scrolling)
        self.context_persistence: dict = {} # Stores counts of consecutive tags e.g. {"phone_usage": 0}
        self.doom_scroll_trigger_threshold: int = getattr(config, 'DOOM_SCROLL_THRESHOLD', 3)

        # Context History (for LMM narrative)
        self.context_history: deque = deque(maxlen=config.HISTORY_WINDOW_SIZE)
        self.last_history_sample_time: float = 0

        # Reflexive Triggers (Window Rules)
        self.last_reflexive_trigger_time: float = 0
        self.reflexive_trigger_cooldown: int = getattr(config, 'REFLEXIVE_WINDOW_COOLDOWN', 300)

        # Voice Triggers
        self.last_voice_trigger_time: float = 0
        self.voice_trigger_cooldown: int = 5 # seconds

        # Content Creation Mode Heuristic
        self.sexual_arousal_threshold = getattr(config, 'SEXUAL_AROUSAL_THRESHOLD', 50)

        self.logger.log_info(f"LogicEngine initialized. Mode: {self.current_mode}")

    def get_mode(self) -> str:
        with self._lock:
            return self.current_mode

    def is_face_detected(self) -> bool:
        with self._lock:
            return self.face_metrics.get("face_detected", False)

    def set_mode(self, mode: str, from_snooze_expiry: bool = False) -> None:
        with self._lock:
            self._set_mode_unlocked(mode, from_snooze_expiry)

    def _set_mode_unlocked(self, mode: str, from_snooze_expiry: bool = False) -> None:
        if mode not in ["active", "snoozed", "paused", "error", "dnd"]:
            self.logger.log_warning(f"Attempted to set invalid mode: {mode}")
            return

        old_mode = self.current_mode
        if mode == old_mode and not from_snooze_expiry:
            if not (mode == "active" and from_snooze_expiry and old_mode == "snoozed"):
                return

        # Reset auto-dnd flag if manual change (or any change not explicitly preserving it)
        self.auto_dnd_active = False

        self.logger.log_info(f"LogicEngine: Changing mode from {old_mode} to {mode}")

        if old_mode != "paused" and mode == "paused":
            self.previous_mode_before_pause = old_mode

        if mode == "active" and old_mode == "error":
             self.logger.log_info("Entered active mode from error. Starting probation period.")
             self.recovery_probation_end_time = time.time() + self.recovery_probation_duration

        self.current_mode = mode

        if self.current_mode == "snoozed":
            self.snooze_end_time = time.time() + config.SNOOZE_DURATION
            self.logger.log_info(f"Snooze activated. Will return to active mode in {config.SNOOZE_DURATION / 60:.0f} minutes.")
        elif self.current_mode == "active":
            self.snooze_end_time = 0

        self._notify_mode_change(old_mode, new_mode=self.current_mode, from_snooze_expiry=from_snooze_expiry)

    def cycle_mode(self) -> None:
        with self._lock:
            current_actual_mode = self.current_mode
            if current_actual_mode == "active":
                self._set_mode_unlocked("snoozed")
            elif current_actual_mode == "snoozed":
                self._set_mode_unlocked("paused")
            elif current_actual_mode == "paused":
                self._set_mode_unlocked("active")

    def toggle_pause_resume(self) -> None:
        with self._lock:
            current_actual_mode = self.current_mode
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

    def register_user_input(self) -> None:
        """
        Registers that user input (keyboard/mouse) has occurred.
        Updates the last input timestamp and enables tracking.
        """
        # Updates are atomic enough for our resolution
        self.last_user_input_time = time.time()
        self.input_tracking_enabled = True

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

                # Prepare video analysis context for LMM
                # We want face metrics plus other relevant high-level signals
                self.video_analysis = self.face_metrics.copy()
                additional_keys = ["posture_state", "vertical_position", "horizontal_position", "normalized_activity"]
                for k in additional_keys:
                    if k in metrics:
                        self.video_analysis[k] = metrics[k]

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

                # STT Buffer logic
                # Only buffer if there's speech confidence or sufficient energy
                is_speech = self.audio_analysis.get("is_speech", False)

                # State transition detection
                if is_speech and not self.last_speech_state:
                    self.speech_start_time = time.time()

                # Append to buffer if speech detected or trailing silence (to complete sentence)
                # Simple logic: if speech, add.
                if is_speech:
                    if len(audio_chunk.shape) > 1:
                        self.audio_buffer_for_stt.extend(audio_chunk[:, 0])
                    else:
                        self.audio_buffer_for_stt.extend(audio_chunk)

                # Trigger logic based on state change (Falling Edge)
                # If speech ENDS (was True, now False), we process the buffer
                if self.last_speech_state and not is_speech:
                    # Delay slightly or check buffer length to ensure we have a sentence?
                    # For now, trigger processing if buffer is big enough
                    if len(self.audio_buffer_for_stt) > 22050: # > 0.5s @ 44.1k
                        self._trigger_stt_processing()

                self.last_speech_state = is_speech

            else:
                # Fallback calculation
                if len(audio_chunk) > 0:
                    self.audio_level = np.sqrt(np.mean(audio_chunk**2))
                else:
                    self.audio_level = 0.0
                self.audio_analysis = {"rms": self.audio_level}

        self.logger.log_debug(f"Processed audio chunk. Level: {self.audio_level:.4f}")

    def _trigger_stt_processing(self):
        """Copies buffer and launches background STT thread."""
        if self.stt_thread and self.stt_thread.is_alive():
            # If busy, maybe skip or queue? For now, skip to avoid lag
            self.logger.log_debug("STT thread busy, skipping chunk.")
            return

        # Copy buffer and clear
        audio_data = np.array(self.audio_buffer_for_stt)
        self.audio_buffer_for_stt.clear()

        sample_rate = 44100
        if self.audio_sensor and hasattr(self.audio_sensor, 'sample_rate'):
            sample_rate = self.audio_sensor.sample_rate

        self.stt_thread = threading.Thread(
            target=self._run_stt_async,
            args=(audio_data, sample_rate),
            daemon=True
        )
        self.stt_thread.start()

    def _run_stt_async(self, audio_data, sample_rate):
        try:
            text = self.stt_interface.transcribe(audio_data, sample_rate)
            if text:
                with self._lock:
                    self.last_transcription = text
                    self.last_transcription_time = time.time()

                self.logger.log_info(f"User Speech Detected: '{text}'")

                # Check Voice Commands Immediately
                if self.intervention_engine:
                    voice_intervention_id = self._check_voice_commands(text)
                    if voice_intervention_id:
                        self.logger.log_info(f"Triggering Voice Command Intervention: {voice_intervention_id}")
                        self.intervention_engine.start_intervention({"id": voice_intervention_id, "tier": 2})
                        with self._lock:
                            self.last_voice_trigger_time = time.time()

        except Exception as e:
            self.logger.log_warning(f"STT Async Error: {e}")

    def _scrub_window_title(self, title: str) -> str:
        """
        Scrubs sensitive information from window titles based on configured keywords.
        Returns "[REDACTED]" if any sensitive keyword is found.
        """
        if not title:
            return title

        # Check against SENSITIVE_APP_KEYWORDS
        title_lower = title.lower()
        # Ensure we have a list to iterate over
        keywords = getattr(config, 'SENSITIVE_APP_KEYWORDS', [])
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return "[REDACTED]"
        return title

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

            # Retrieve recent speech context
            # Only send if recent (< 30s)
            speech_context = None
            if self.last_transcription and (time.time() - self.last_transcription_time < 30):
                speech_context = self.last_transcription

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

            # Check for Rapid Task Switching
            rapid_switch_threshold = getattr(config, 'RAPID_SWITCHING_THRESHOLD', 4)
            # Only check if we have enough history to possibly meet the threshold
            if len(self.context_history) >= rapid_switch_threshold:
                unique_windows = {snap.get('active_window') for snap in self.context_history if snap.get('active_window')}
                if len(unique_windows) >= rapid_switch_threshold:
                    system_alerts.append("Rapid Task Switching Detected")

            active_window = "Unknown"
            if self.window_sensor:
                try:
                    raw_window = self.window_sensor.get_active_window()
                    active_window = self._scrub_window_title(raw_window)
                except Exception as e:
                    self.logger.log_debug(f"Error fetching active window: {e}")

            context = {
                "current_mode": self.current_mode,
                "context_history": list(self.context_history),
                "trigger_reason": trigger_reason,
                "active_window": active_window,
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
                "preferred_interventions": preferred_list,
                "user_speech": speech_context
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
                is_fallback = analysis.get("_meta", {}).get("is_fallback", False)

                with self._lock:
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
                    reflexive_intervention_id = self._process_visual_context_triggers(visual_context)
                    triggered_intervention_id = reflexive_intervention_id

                # Log state update event
                self.logger.log_event("state_update", self.state_engine.get_state())

                # Trigger Mood Playlist (Music Integration)
                # Only play music if enabled in config and not in fallback mode (to avoid startup noise)
                music_enabled = getattr(config, 'ENABLE_MUSIC_CONTROL', False)
                if self.music_interface and music_enabled and not is_fallback:
                    try:
                        state = self.state_engine.get_state()
                        self.music_interface.play_mood_playlist(
                            mood=state.get("mood", 50),
                            arousal=state.get("arousal", 50),
                            sexual_arousal=state.get("sexual_arousal", 0)
                        )
                    except Exception as e:
                        self.logger.log_warning(f"Music Interface Error: {e}")

                # Update tray tooltip with new state
                if hasattr(self, 'state_update_callback') and self.state_update_callback:
                    self.state_update_callback(self.state_engine.get_state())

            else:
                 # LogicEngine received None (hard failure in interface even after retries and no fallback?)
                 # This usually means no fallback was enabled or interface crashed.
                 with self._lock:
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
            with self._lock:
                self.lmm_consecutive_failures += 1

    def _process_visual_context_triggers(self, visual_context: list) -> Optional[str]:
        """
        Analyzes visual context tags for persistent patterns (e.g., Doom Scrolling).
        Returns an intervention ID string if a specific persistent trigger is met, else None.
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

    def _check_window_reflexes(self, active_window: str) -> Optional[str]:
        """
        Checks if the active window matches any reflexive trigger rules.
        Returns the intervention ID if matched and eligible (cooldown), else None.
        """
        current_time = time.time()
        if current_time - self.last_reflexive_trigger_time < self.reflexive_trigger_cooldown:
            return None

        if not active_window:
            return None

        active_window_lower = active_window.lower()

        # 1. Custom/Advanced Triggers (Priority)
        reflex_rules = getattr(config, 'REFLEXIVE_WINDOW_TRIGGERS', {})
        if reflex_rules:
            for keyword, intervention_id in reflex_rules.items():
                if keyword.lower() in active_window_lower:
                    # Log safe message
                    self.logger.log_info(f"Reflexive Window Match (Advanced): '{keyword}' found in active window.")
                    return intervention_id

        # 2. Focus Apps (Safe List)
        # If in a Focus App, suppress Distraction checks
        focus_apps = getattr(config, 'FOCUS_APPS', [])
        for app in focus_apps:
            if app.lower() in active_window_lower:
                self.logger.log_debug(f"Focus App Active: '{app}'. Suppressing distraction checks.")
                return None # Explicitly safe

        # 3. Distraction Apps (Standard)
        distraction_apps = getattr(config, 'DISTRACTION_APPS', [])
        for app in distraction_apps:
            if app.lower() in active_window_lower:
                self.logger.log_info(f"Distraction App Detected: '{app}'")
                return "distraction_alert"

        return None

    def _check_voice_commands(self, text: str) -> Optional[str]:
        """
        Checks if transcribed text matches any voice commands.
        """
        current_time = time.time()
        if current_time - self.last_voice_trigger_time < self.voice_trigger_cooldown:
            return None

        commands = getattr(config, 'VOICE_COMMANDS', {})
        if not commands or not text:
            return None

        text_lower = text.lower()
        for phrase, intervention_id in commands.items():
            if phrase.lower() in text_lower:
                self.logger.log_info(f"Voice Command Match: '{phrase}' found in speech.")
                return intervention_id

        return None

    def _run_offline_fallback_logic(self, reason: str) -> None:
        """
        Executes simple heuristic-based interventions when LMM is offline.
        """
        current_time = time.time()
        if current_time - self.last_offline_trigger_time < self.offline_trigger_interval:
            self.logger.log_debug(f"Offline fallback skipped: Cooldown active ({int(self.offline_trigger_interval - (current_time - self.last_offline_trigger_time))}s left).")
            return

        intervention_payload = None

        if reason == "high_audio_level":
            intervention_payload = {
                "type": "offline_noise_reduction",
                "message": "It's getting a bit loud, and I'm currently offline. You might want to lower the volume or take a break.",
                "tier": 1
            }
        elif reason == "high_video_activity":
            intervention_payload = {
                "type": "offline_activity_reduction",
                "message": "I'm detecting a lot of movement, but I can't reach the cloud. Maybe take a moment to settle?",
                "tier": 1
            }

        if intervention_payload and self.intervention_engine:
            self.logger.log_info(f"Triggering Offline Fallback Intervention: {reason}")
            self.intervention_engine.start_intervention(intervention_payload)
            self.last_offline_trigger_time = current_time

    def _trigger_lmm_analysis(self, reason: str = "unknown", allow_intervention: bool = True) -> None:
        if not self.lmm_interface:
            self.logger.log_warning("LMM interface not available.")
            return

        # Check Circuit Breaker
        with self._lock:
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

        trigger_payload = {
            "reason": reason,
            "metrics": lmm_payload["user_context"].get("sensor_metrics", {})
        }
        self.logger.log_event("lmm_trigger", trigger_payload)

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
            # Check Reflexive Window Triggers
            if self.window_sensor and self.intervention_engine:
                try:
                    # Use raw window title for checking reflexes (we need the app name)
                    # Note: _check_window_reflexes logs safely (without exposing title)
                    active_win = self.window_sensor.get_active_window(sanitize=False)
                    reflex_id = self._check_window_reflexes(active_win)
                    if reflex_id:
                        self.logger.log_info(f"Triggering Reflexive Intervention: {reflex_id}")
                        self.intervention_engine.start_intervention({
                            "id": reflex_id,
                            "tier": 2 # Escalated tier for distraction
                        })
                        self.last_reflexive_trigger_time = time.time()
                except Exception as e:
                    # Don't let window check crash the loop
                    pass

        if current_mode in ["active", "dnd"]:
            current_time = time.time()

            # Check probation
            if self.recovery_probation_end_time > 0 and current_time > self.recovery_probation_end_time:
                self.logger.log_info("Error recovery probation passed. Resetting error counters.")
                self.error_recovery_attempts = 0
                self.recovery_probation_end_time = 0

            trigger_lmm = False
            trigger_reason = ""

            # 1. Process sensor data & Evaluate conditions (Metrics updated in process_* methods)
            with self._lock:
                current_audio_level = self.audio_level
                current_video_activity = self.video_activity
                # Get more detailed analysis for filtering triggers
                is_speech = self.audio_analysis.get("is_speech", False)
                face_detected = self.face_metrics.get("face_detected", False)
                face_count = self.face_metrics.get("face_count", 0)

                # Snapshot current state for history (Lock held)
                if current_time - self.last_history_sample_time >= config.HISTORY_SAMPLE_INTERVAL:
                    self.last_history_sample_time = current_time

                    # Fetch active window safely (might take time, but usually fast enough; ideally async but sensor is local)
                    hist_active_window = "Unknown"
                    if self.window_sensor:
                        try:
                            raw_hist_window = self.window_sensor.get_active_window()
                            hist_active_window = self._scrub_window_title(raw_hist_window)
                        except: pass

                    snapshot = {
                        "timestamp": current_time,
                        "mode": self.current_mode,
                        "active_window": hist_active_window,
                        "audio_level": current_audio_level,
                        "video_activity": current_video_activity,
                        "face_detected": face_detected,
                        "posture": self.video_analysis.get("posture_state", "unknown")
                    }
                    self.context_history.append(snapshot)

            # 2. Check Meeting Mode Conditions (Active -> DND)
            if self.input_tracking_enabled:
                idle_time = current_time - self.last_user_input_time
                speech_duration_threshold = getattr(config, 'MEETING_MODE_SPEECH_DURATION_THRESHOLD', 3.0)
                idle_threshold = getattr(config, 'MEETING_MODE_IDLE_KEYBOARD_THRESHOLD', 10.0)

                # Track speech duration
                if is_speech and face_detected:
                    self.last_speech_time = current_time
                    if self.continuous_speech_start_time == 0:
                        self.continuous_speech_start_time = current_time
                else:
                    grace_period = getattr(config, 'MEETING_MODE_SPEECH_GRACE_PERIOD', 2.0)
                    if self.continuous_speech_start_time > 0:
                        if current_time - self.last_speech_time > grace_period:
                            self.continuous_speech_start_time = 0
                    else:
                        self.continuous_speech_start_time = 0

                # Check thresholds
                speech_duration = 0
                if self.continuous_speech_start_time > 0:
                    speech_duration = current_time - self.continuous_speech_start_time

                if (speech_duration >= speech_duration_threshold and
                    idle_time >= idle_threshold and
                    face_detected):

                    if self.current_mode == "active": # Only switch if currently active
                        self.logger.log_info(f"Meeting Mode Detected! (Speech: {speech_duration:.1f}s, Idle: {idle_time:.1f}s). Switching to DND.")
                        self.set_mode("dnd")
                        self.auto_dnd_active = True
                        if self.notification_callback:
                            self.notification_callback("Meeting Detected", "Switching to Do Not Disturb mode.")

            # Exit Meeting Mode (Auto-DND -> Active)
            if self.current_mode == "dnd" and self.auto_dnd_active and self.input_tracking_enabled:
                 idle_time = current_time - self.last_user_input_time
                 if idle_time < 1.0:
                     self.logger.log_info("User activity detected during Auto-DND. Exiting Meeting Mode.")
                     self.set_mode("active")

            # 3. Check for Event-based triggers
            if current_audio_level > self.audio_threshold_high:
                if is_speech:
                    if current_time - self.last_lmm_call_time >= self.min_lmm_interval:
                        trigger_lmm = True
                        trigger_reason = "high_audio_level"
                else:
                    self.logger.log_debug(f"High audio level ({current_audio_level:.2f}) ignored: Not speech.")

            elif current_video_activity > self.video_activity_threshold_high:
                if face_detected or face_count > 0:
                    if current_time - self.last_lmm_call_time >= self.min_lmm_interval:
                        trigger_lmm = True
                        trigger_reason = "high_video_activity"
                else:
                    self.logger.log_debug(f"High video activity ({current_video_activity:.2f}) ignored: No face detected.")

            # 3. Periodic Check (Heartbeat)
            if not trigger_lmm:
                if current_time - self.last_lmm_call_time >= self.lmm_call_interval:
                    trigger_lmm = True
                    trigger_reason = "periodic_check"

            # 4. Trigger LMM if warranted
            if trigger_lmm:
                self.last_lmm_call_time = current_time
                # Intervention only allowed in 'active' mode
                should_intervene = (current_mode == "active")

                # Check Circuit Breaker
                circuit_open = False
                with self._lock:
                    if time.time() < self.lmm_circuit_breaker_open_until:
                        circuit_open = True

                if circuit_open:
                     self.logger.log_info(f"LMM Circuit Open. Attempting Offline Fallback (Reason: {trigger_reason})")
                     if should_intervene:
                        self._run_offline_fallback_logic(reason=trigger_reason)
                else:
                    self._trigger_lmm_analysis(reason=trigger_reason, allow_intervention=should_intervene)

            # 5. Check Content Creation Mode
            # If sexual_arousal > threshold, we might want to temporarily increase LMM frequency
            # or trigger specific interventions more aggressively.

            with self._lock:
                current_sexual_arousal = self.state_engine.get_state().get("sexual_arousal", 0)

            if current_sexual_arousal > self.sexual_arousal_threshold:
                 # In high sexual arousal state, we might want to ensure LMM checks more frequently
                 # to capture the "moment".
                 if current_time - self.last_lmm_call_time >= (self.lmm_call_interval / 2): # Check twice as often
                     if not trigger_lmm: # If not already triggered
                        self.logger.log_info(f"High Sexual Arousal ({current_sexual_arousal}) detected. Triggering accelerated LMM check.")
                        self._trigger_lmm_analysis(reason="high_sexual_arousal", allow_intervention=True)

        elif current_mode == "error":
            current_time = time.time()
            if current_time - self.last_error_log_time > 10:
                self.logger.log_debug("LogicEngine: Mode is ERROR. Attempting to handle or log.")
                self.last_error_log_time = current_time

            if self.error_recovery_attempts < self.max_error_recovery_attempts:
                if current_time - self.last_error_recovery_attempt_time > self.error_recovery_interval:
                    self.logger.log_info(f"Attempting error recovery ({self.error_recovery_attempts + 1}/{self.max_error_recovery_attempts})...")
                    self.last_error_recovery_attempt_time = current_time
                    self.error_recovery_attempts += 1

                    target_mode = self.previous_mode_before_pause if self.previous_mode_before_pause != "error" else "active"
                    self.logger.log_info(f"Resetting mode to {target_mode} for recovery check.")
                    self.set_mode(target_mode)

            elif self.error_recovery_attempts == self.max_error_recovery_attempts:
                self.logger.log_error("Max error recovery attempts reached. User intervention required.")
                if self.notification_callback:
                    self.notification_callback("System Error", "The system has encountered a persistent error and could not recover automatically. Please check logs.")
                self.error_recovery_attempts += 1

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
            self.lmm_thread.join(timeout=2.0)
            if self.lmm_thread.is_alive():
                self.logger.log_warning("LMM analysis thread did not finish in time (will be killed as daemon).")
            else:
                self.logger.log_info("LMM analysis thread finished.")

        if self.stt_thread and self.stt_thread.is_alive():
            self.logger.log_info("Waiting for STT thread to finish...")
            self.stt_thread.join(timeout=2.0)
            if self.stt_thread.is_alive():
                self.logger.log_warning("STT thread did not finish in time.")
