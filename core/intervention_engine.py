import time
import config
import datetime
import threading
from typing import Optional, Any, Dict
from .intervention_library import InterventionLibrary

class InterventionEngine:
    def __init__(self, logic_engine: Any, app_instance: Optional[Any] = None) -> None:
        self.logic_engine = logic_engine
        self.app = app_instance
        self.library = InterventionLibrary()
        self.last_intervention_time: float = 0
        self._intervention_active: threading.Event = threading.Event()
        self.intervention_thread: Optional[threading.Thread] = None
        self._current_intervention_details: Dict[str, Any] = {}

        # Dictionary to store suppressed interventions: {intervention_id_or_type: expiry_timestamp}
        self.suppressed_interventions: Dict[str, float] = {}

        self.last_feedback_eligible_intervention: Dict[str, Any] = {
            "message": None,
            "type": None,
            "timestamp": None
        }
        self.feedback_window: int = config.FEEDBACK_WINDOW_SECONDS if hasattr(config, 'FEEDBACK_WINDOW_SECONDS') else 15

        log_message = "InterventionEngine initialized."
        if self.app and hasattr(self.app, 'data_logger'):
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message + " (DataLogger not available)")

    def _store_last_intervention(self, message: str, intervention_type_for_logging: str) -> None:
        """Stores details of an intervention that qualifies for feedback."""
        self.last_feedback_eligible_intervention = {
            "message": message,
            "type": intervention_type_for_logging,
            "timestamp": time.time()
        }
        if self.app and self.app.data_logger:
             self.app.data_logger.log_debug(f"Stored intervention for feedback: Type='{intervention_type_for_logging}', Msg='{message}'")

    def _speak(self, text: str) -> None:
        # Placeholder for actual text-to-speech (TTS) implementation
        log_message = f"SPEAKING: '{text}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)

    def _play_sound(self, sound_file_path: str) -> None:
        # Placeholder for playing a sound
        log_message = f"PLAYING_SOUND: '{sound_file_path}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)

    def _show_visual_prompt(self, image_path_or_text: str) -> None:
        # Placeholder for showing a visual prompt (e.g., a window with an image or text)
        log_message = f"SHOWING_VISUAL: '{image_path_or_text}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)


    def _run_intervention_thread(self) -> None:
        """The actual intervention logic run in a separate thread."""
        details = self._current_intervention_details
        intervention_type = details.get("type", "unknown_intervention")
        # message field might be overridden by the sequence, but keeps backward compatibility
        message = details.get("message", "Intervention started.")

        # Determine sequence
        sequence = details.get("sequence", [])
        if not sequence:
            # Fallback to legacy single-message behavior if no sequence provided
            sequence = [{"action": "speak", "text": message}]

        # Duration is less strict now, as sequence drives it, but we keep a safety timeout
        max_duration = details.get("duration", 300)

        start_time = time.time()

        log_prefix = f"Intervention (Type: {intervention_type})"
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None

        def log_info(msg: str) -> None:
            if logger: logger.log_info(msg)
            else: print(msg)

        log_info(f"{log_prefix}: Started.")

        # Store for feedback immediately (or we could do it after, but user might feedback during)
        if intervention_type not in ["mode_change_notification", "error_notification_spoken"]:
            self._store_last_intervention(message, intervention_type)

        # Flash tray icon
        current_app_mode = self.logic_engine.get_mode()
        if self.app and hasattr(self.app, 'tray_icon') and self.app.tray_icon:
             if intervention_type not in ["mode_change_notification"]:
                flash_icon_type = "error" if "error" in intervention_type else "active"
                self.app.tray_icon.flash_icon(flash_status=flash_icon_type, original_status=current_app_mode)

        # Execute Sequence
        for step in sequence:
            if not self._intervention_active.is_set():
                log_info(f"{log_prefix}: Stopped early by request.")
                break

            action = step.get("action")

            if action == "speak":
                text = step.get("text", "")
                self._speak(text)
            elif action == "wait":
                duration = step.get("duration", 1)
                # Wait in small chunks to allow interruption
                waited = 0
                while waited < duration and self._intervention_active.is_set():
                    time.sleep(0.1)
                    waited += 0.1
            elif action == "play_sound":
                self._play_sound(step.get("file", "default.wav"))
            elif action == "show_visual":
                self._show_visual_prompt(step.get("content", ""))

            # Check total timeout
            if (time.time() - start_time) > max_duration:
                log_info(f"{log_prefix}: Max duration exceeded.")
                break

        log_info(f"{log_prefix}: Completed.")
        self._intervention_active.clear()
        self._current_intervention_details = {}

    def start_intervention(self, intervention_details: Dict[str, Any]) -> bool:
        """
        Starts an intervention.
        intervention_details can be:
        1. A full dict with 'type', 'message' (legacy)
        2. A dict with 'id' pointing to a library intervention.
        """
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None

        # Resolve intervention from library if 'id' is present
        final_details = intervention_details.copy()
        if "id" in final_details:
             lib_entry = self.library.get_intervention(final_details["id"])
             if lib_entry:
                 # Merge library entry, letting passed details override (e.g. custom message)
                 # But usually library entry is the source of truth for sequence
                 final_details = {**lib_entry, **final_details}
                 # Map 'id' to 'type' if 'type' is missing, for consistency
                 if "type" not in final_details:
                     final_details["type"] = final_details["id"]
                 # Ensure 'message' exists for logging/feedback if not in details
                 if "message" not in final_details and "description" in final_details:
                     final_details["message"] = final_details["description"]

        intervention_type = final_details.get("type")
        # Check suppression
        current_time = time.time()
        if intervention_type in self.suppressed_interventions:
            expiry = self.suppressed_interventions[intervention_type]
            if current_time < expiry:
                msg = f"Intervention '{intervention_type}' suppressed by user feedback until {datetime.datetime.fromtimestamp(expiry).strftime('%H:%M:%S')}."
                if logger: logger.log_info(msg)
                else: print(msg)
                return False
            else:
                # Expired, clean up
                del self.suppressed_interventions[intervention_type]

        # We relax the check for 'message' if 'sequence' is present
        has_sequence = "sequence" in final_details and len(final_details["sequence"]) > 0
        message = final_details.get("message")

        if not intervention_type or (not message and not has_sequence):
            if logger:
                logger.log_warning("Intervention attempt failed: 'type' and ('message' or 'sequence') are required.")
            else:
                print("Intervention attempt failed: 'type' and ('message' or 'sequence') are required.")
            return False

        if self._intervention_active.is_set():
            if logger:
                logger.log_info(f"Intervention attempt ignored: An intervention ('{self._current_intervention_details.get('type')}') is already active.")
            else:
                print(f"Intervention attempt ignored: An intervention ('{self._current_intervention_details.get('type')}') is already active.")
            return False

        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            if logger:
                logger.log_info(f"Intervention '{intervention_type}' suppressed: Mode is {current_app_mode}")
            else:
                print(f"Intervention '{intervention_type}' suppressed: Mode is {current_app_mode}")
            return False

        current_time = time.time()
        if intervention_type not in ["mode_change_notification", "error_notification", "error_notification_spoken"] and \
           (current_time - self.last_intervention_time < config.MIN_TIME_BETWEEN_INTERVENTIONS):
            if logger:
                logger.log_info(f"Intervention '{intervention_type}' suppressed: Too soon since last intervention.")
            else:
                print(f"Intervention '{intervention_type}' suppressed: Too soon since last intervention.")
            return False

        self._intervention_active.set()

        # Populate details with defaults
        if "duration" not in final_details:
            # Estimate duration from sequence if possible?
            # For now use default max
            final_details["duration"] = config.DEFAULT_INTERVENTION_DURATION * 2 # sequences might be long

        self._current_intervention_details = final_details
        self.last_intervention_time = current_time

        self.intervention_thread = threading.Thread(target=self._run_intervention_thread)
        self.intervention_thread.daemon = True
        self.intervention_thread.start()

        log_msg = f"Intervention '{intervention_type}' initiated."
        if has_sequence: log_msg += f" (Sequence len: {len(final_details['sequence'])})"

        if logger: logger.log_info(log_msg)
        else: print(log_msg)

        return True

    def stop_intervention(self) -> None:
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None
        if self._intervention_active.is_set() and self.intervention_thread:
            if logger:
                logger.log_info(f"Stopping intervention ('{self._current_intervention_details.get('type')}', Tier {self._current_intervention_details.get('tier')})...")
            else:
                print(f"Stopping intervention ('{self._current_intervention_details.get('type')}', Tier {self._current_intervention_details.get('tier')})...")
            self._intervention_active.clear()
        else:
            if logger:
                logger.log_info("No active intervention to stop.")
            else:
                print("No active intervention to stop.")

    def notify_mode_change(self, new_mode: str, custom_message: Optional[str] = None) -> None:
        """Handles speaking notifications for mode changes. These are not subject to feedback."""
        message = custom_message
        if not message:
            if new_mode == "paused":
                message = "Co-regulator paused."
            elif new_mode == "snoozed":
                message = f"Co-regulator snoozed for {config.SNOOZE_DURATION / 60:.0f} minutes."
            elif new_mode == "active":
                message = "Co-regulator active."
            elif new_mode == "error":
                message = "Sensor error detected. Operations affected."

        if message:
            self._speak(message)

    def register_feedback(self, feedback_value: str) -> None:
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None
        if not self.last_feedback_eligible_intervention["timestamp"]:
            log_msg = "Feedback received, but no recent feedback-eligible intervention to link it to."
            if logger:
                logger.log_info(log_msg)
            else:
                print(log_msg)
            return

        time_since_intervention = time.time() - self.last_feedback_eligible_intervention["timestamp"]

        if time_since_intervention > self.feedback_window:
            log_msg = f"Feedback ('{feedback_value}') received for intervention '{self.last_feedback_eligible_intervention['message']}', but too late."
            if logger:
                logger.log_info(log_msg)
            else:
                print(log_msg)
            self.last_feedback_eligible_intervention = {"message": None, "type": None, "timestamp": None}
            return

        feedback_payload = {
            "intervention_message": self.last_feedback_eligible_intervention["message"],
            "intervention_type": self.last_feedback_eligible_intervention["type"],
            "feedback_value": feedback_value,
            "timestamp_of_intervention": datetime.datetime.fromtimestamp(self.last_feedback_eligible_intervention["timestamp"]).isoformat(),
            "timestamp_of_feedback": datetime.datetime.now().isoformat(),
            "time_delta_seconds": round(time_since_intervention, 2)
        }

        # Apply suppression if feedback is unhelpful
        if feedback_value.lower() == "unhelpful":
            suppression_minutes = config.FEEDBACK_SUPPRESSION_MINUTES if hasattr(config, 'FEEDBACK_SUPPRESSION_MINUTES') else 240
            expiry = time.time() + (suppression_minutes * 60)
            int_type = self.last_feedback_eligible_intervention["type"]
            self.suppressed_interventions[int_type] = expiry
            if logger:
                logger.log_info(f"Feedback 'unhelpful' received. Suppressing '{int_type}' for {suppression_minutes} minutes.")

        log_msg_console = f"Feedback '{feedback_value}' logged for intervention: '{self.last_feedback_eligible_intervention['message']}'"
        if logger:
            logger.log_event(event_type="user_feedback", payload=feedback_payload)
            logger.log_info(log_msg_console)
        else:
            print(f"DataLogger not available. Feedback event: {feedback_payload}")

        self.last_feedback_eligible_intervention = {"message": None, "type": None, "timestamp": None}


if __name__ == '__main__':
    # Enhanced MockApp for testing
    class MockDataLogger:
        def log_info(self, msg): print(f"MOCK_LOG_INFO: {msg}")
        def log_debug(self, msg): print(f"MOCK_LOG_DEBUG: {msg}")
        def log_warning(self, msg): print(f"MOCK_LOG_WARN: {msg}")
        def log_error(self, msg, details=""): print(f"MOCK_LOG_ERROR: {msg} | Details: {details}")
        def log_event(self, event_type, payload):
            print(f"MOCK_LOG_EVENT: Type='{event_type}', Payload='{payload}'")

    class MockLogicEngine:
        def __init__(self): self.mode = "active"
        def get_mode(self): return self.mode
        def set_mode(self, mode): self.mode = mode

    class MockTrayIcon:
        def flash_icon(self, flash_status, original_status):
            print(f"MOCK_TRAY_ICON: Flashing with '{flash_status}' from '{original_status}'.")

    class MockApp:
        def __init__(self):
            self.tray_icon = MockTrayIcon()
            self.data_logger = MockDataLogger()
            if not hasattr(config, 'FEEDBACK_WINDOW_SECONDS'):
                config.FEEDBACK_WINDOW_SECONDS = 15
            if not hasattr(config, 'MIN_TIME_BETWEEN_INTERVENTIONS'): # Default if not in config
                config.MIN_TIME_BETWEEN_INTERVENTIONS = 10
            # Ensure it's defined for the test default duration calculation
            if hasattr(config, 'MIN_TIME_BETWEEN_INTERVENTIONS') and config.MIN_TIME_BETWEEN_INTERVENTIONS == 0:
                 config.MIN_TIME_BETWEEN_INTERVENTIONS = 10 # Avoid division by zero if set to 0
            print("MockApp for InterventionEngine test created.")

    mock_logic_engine = MockLogicEngine()
    mock_app_instance = MockApp()
    intervention_engine = InterventionEngine(mock_logic_engine, mock_app_instance)

    print("\n--- Test 1: Tier 1 Intervention (Default) ---")
    details_t1 = {"type": "posture_check", "message": "Sit straight!", "duration": 0.1}
    intervention_engine.start_intervention(details_t1)
    time.sleep(0.2)

    print("\n--- Test 2: Library Intervention (Box Breathing) ---")
    # We modify the sequence in library for test speed
    box_breathing_id = "phys_box_breathing"
    lib_entry = intervention_engine.library.get_intervention(box_breathing_id)
    # Patch the sequence to be faster for test
    lib_entry["sequence"] = [
        {"action": "speak", "text": "Start test breathing."},
        {"action": "wait", "duration": 0.1},
        {"action": "speak", "text": "End test breathing."}
    ]
    intervention_engine.start_intervention({"id": box_breathing_id})
    time.sleep(0.5)

    print("\n--- Test 3: Tier 3 Intervention and stop early ---")
    details_t3 = {"type": "emergency_break", "message": "Mandatory break time!", "tier": 3, "duration": 0.5}
    intervention_engine.start_intervention(details_t3)
    time.sleep(0.1)
    intervention_engine.stop_intervention()
    time.sleep(0.1)

    print("\n--- Test 4: Start Intervention with missing type/message ---")
    intervention_engine.start_intervention({"message": "This will fail", "duration": 1})
    intervention_engine.start_intervention({"type": "fail_test", "duration": 1})
    time.sleep(0.5)

    print("\n--- Test 5: Attempt to start intervention while another is active ---")
    details_active = {"type": "break_reminder", "message": "Take a break!", "duration": 0.2}
    intervention_engine.start_intervention(details_active)
    time.sleep(0.1)
    details_ignored = {"type": "second_break", "message": "Seriously, break time!", "tier": 1, "duration": 0.1}
    intervention_engine.start_intervention(details_ignored) # Should be ignored
    time.sleep(0.2)

    print("\n--- Test 6: Intervention suppressed due to mode not 'active' ---")
    mock_logic_engine.set_mode("paused")
    details_paused = {"type": "posture_check_paused", "message": "Posture in pause?", "duration": 0.1}
    intervention_engine.start_intervention(details_paused)
    mock_logic_engine.set_mode("active")
    time.sleep(0.1)

    print("\n--- Test 7: Intervention suppressed due to MIN_TIME_BETWEEN_INTERVENTIONS ---")
    config.MIN_TIME_BETWEEN_INTERVENTIONS = 5
    intervention_engine.last_intervention_time = time.time() - 1
    details_too_soon = {"type": "too_soon_test", "message": "Am I too soon?", "duration": 0.1}
    intervention_engine.start_intervention(details_too_soon)
    time.sleep(0.1)
    config.MIN_TIME_BETWEEN_INTERVENTIONS = 0.1 # Reset for other tests


    print("\n--- Test 8: Feedback for a Tier 2 completed intervention ---")
    details_feedback = {"type": "feedback_test_tier2", "message": "Was this Tier 2 helpful?", "tier": 2, "duration": 0.1}
    intervention_engine.start_intervention(details_feedback)
    time.sleep(0.2)
    intervention_engine.register_feedback("helpful")
    time.sleep(0.1)

    print("\n--- Test 9: Mode Change Notification (separate from threaded interventions) ---")
    intervention_engine.notify_mode_change("snoozed")
    time.sleep(0.1)

    if intervention_engine.intervention_thread and intervention_engine.intervention_thread.is_alive():
        print("Waiting for active intervention thread to finish before exiting test...")
        intervention_engine.stop_intervention()
        intervention_engine.intervention_thread.join(timeout=2)

    print("\nInterventionEngine tests complete.")
