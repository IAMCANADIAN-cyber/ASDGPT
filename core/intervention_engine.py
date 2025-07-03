import time
import config
import datetime # For feedback timestamping
import threading

class InterventionEngine:
    def __init__(self, logic_engine, app_instance=None):
        self.logic_engine = logic_engine
        self.app = app_instance # Used for DataLogger and TrayIcon
        self.last_intervention_time = 0 # For MIN_TIME_BETWEEN_INTERVENTIONS check
        self.intervention_active = False
        self.intervention_thread = None
        # _current_intervention_details will store: type, message, duration, tier, and other params
        self._current_intervention_details = {}

        # Store details of the last intervention that is eligible for feedback
        self.last_feedback_eligible_intervention = {
            "message": None,
            "type": None, # The specific type of intervention, e.g., "slumped_posture_alert"
            "timestamp": None
        }
        self.feedback_window = config.FEEDBACK_WINDOW_SECONDS if hasattr(config, 'FEEDBACK_WINDOW_SECONDS') else 15

        log_message = "InterventionEngine initialized."
        if self.app and hasattr(self.app, 'data_logger'):
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message + " (DataLogger not available)")

    def _store_last_intervention(self, message, intervention_type_for_logging):
        """Stores details of an intervention that qualifies for feedback."""
        self.last_feedback_eligible_intervention = {
            "message": message,
            "type": intervention_type_for_logging,
            "timestamp": time.time()
        }
        if self.app and self.app.data_logger:
             self.app.data_logger.log_debug(f"Stored intervention for feedback: Type='{intervention_type_for_logging}', Msg='{message}'")

    def _speak(self, text):
        # Placeholder for actual text-to-speech (TTS) implementation
        log_message = f"SPEAKING: '{text}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)
        # Actual TTS would go here

    def _play_sound(self, sound_file_path):
        # Placeholder for playing a sound
        log_message = f"PLAYING_SOUND: '{sound_file_path}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)
        # Actual sound playing library would be used here (e.g., playsound, pygame.mixer)

    def _show_visual_prompt(self, image_path_or_text):
        # Placeholder for showing a visual prompt (e.g., a window with an image or text)
        log_message = f"SHOWING_VISUAL: '{image_path_or_text}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)
        # Actual GUI toolkit would be used here (e.g., tkinter, PyQt)


    def _run_intervention_thread(self):
        """The actual intervention logic run in a separate thread."""
        intervention_type = self._current_intervention_details.get("type", "unknown_intervention")
        message = self._current_intervention_details.get("message", "No message provided.")
        max_duration = self._current_intervention_details.get("duration", config.MIN_TIME_BETWEEN_INTERVENTIONS)
        tier = self._current_intervention_details.get("tier", 1) # Default to Tier 1

        start_time = time.time()
        elapsed_time = 0

        log_prefix = f"Intervention (Type: {intervention_type}, Tier: {tier})"
        logger = self.app.data_logger if self.app and self.app.data_logger else None

        def log_info(msg):
            if logger: logger.log_info(msg)
            else: print(msg)

        def log_debug(msg):
            if logger: logger.log_debug(msg)
            else: print(msg)

        log_info(f"{log_prefix}: Started. Message: '{message}'. Max duration: {max_duration}s.")

        # --- Tier-based intervention execution ---
        if tier == 1: # Simple text prompt
            self._speak(message)
        elif tier == 2: # Guided breathing, calming image/audio
            self._speak(message) # Initial prompt
            # Example: Play a short calming sound
            self._play_sound("path/to/tier2_calm_sound.wav") # Placeholder path
            log_info(f"{log_prefix}: Tier 2 action (e.g., sound) performed.")
        elif tier == 3: # Force break, alert support contact
            self._speak(f"Important: {message}") # More insistent
            # Example: Show a visual prompt to take a break
            self._show_visual_prompt("Take a 5-minute break now.") # Placeholder
            log_info(f"{log_prefix}: Tier 3 action (e.g., visual prompt) performed.")
        else: # Default or unknown tier
            self._speak(message)
            log_info(f"{log_prefix}: Executed default action for unknown tier {tier}.")

        # Store for feedback *after* primary action of intervention, so it's a "delivered" intervention
        if intervention_type not in ["mode_change_notification", "error_notification_spoken"]:
            self._store_last_intervention(message, intervention_type) # Storing original type for feedback consistency

        # Flash tray icon if applicable
        current_app_mode = self.logic_engine.get_mode()
        if self.app and hasattr(self.app, 'tray_icon') and self.app.tray_icon:
            if intervention_type not in ["mode_change_notification"]:
                log_debug(f"{log_prefix}: Flashing tray icon.")
                flash_icon_type = "error" if "error" in intervention_type else "active"
                self.app.tray_icon.flash_icon(flash_status=flash_icon_type, original_status=current_app_mode)

        # Main loop for the intervention duration, allowing for early stop
        while self.intervention_active and elapsed_time < max_duration:
            # Tier-specific ongoing actions could be added here if needed (e.g. repeating a sound softly)
            time.sleep(0.1) # Check frequently for stop signal
            elapsed_time = time.time() - start_time

        if not self.intervention_active:
            log_info(f"{log_prefix}: Stopped early by request.")
        elif elapsed_time >= max_duration:
            log_info(f"{log_prefix}: Completed (duration: {elapsed_time:.1f}s).")

        self.intervention_active = False # Ensure flag is reset
        self._current_intervention_details = {} # Clear details

    def start_intervention(self, intervention_details):
        """
        Starts an intervention based on the provided details.
        intervention_details (dict): Must contain 'type', 'message'.
                                     Optional: 'duration', 'tier', and other parameters.
        """
        log_func = print
        if self.app and self.app.data_logger:
            log_func = self.app.data_logger.log_info

        intervention_type = intervention_details.get("type")
        custom_message = intervention_details.get("message")

        if not intervention_type or not custom_message:
            log_func("Intervention attempt failed: 'type' and 'message' are required in intervention_details.")
            return False

        if self.intervention_active:
            log_func(f"Intervention attempt ignored: An intervention ('{self._current_intervention_details.get('type')}') is already active.")
            return False

        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            log_func(f"Intervention '{intervention_type}' suppressed: Mode is {current_app_mode}")
            return False

        current_time = time.time()
        if intervention_type not in ["mode_change_notification", "error_notification", "error_notification_spoken"] and \
           (current_time - self.last_intervention_time < config.MIN_TIME_BETWEEN_INTERVENTIONS):
            log_func(f"Intervention '{intervention_type}' suppressed: Too soon since last intervention ({current_time - self.last_intervention_time:.1f}s < {config.MIN_TIME_BETWEEN_INTERVENTIONS}s).")
            return False

        self.intervention_active = True

        # Populate _current_intervention_details, ensuring defaults
        self._current_intervention_details = {
            "type": intervention_type,
            "message": custom_message,
            "duration": intervention_details.get("duration", config.DEFAULT_INTERVENTION_DURATION), # Use new default duration
            "tier": intervention_details.get("tier", 1), # Default to Tier 1
            # Allow any other parameters to be passed through
            **{k: v for k, v in intervention_details.items() if k not in ["type", "message", "duration", "tier"]}
        }

        self.last_intervention_time = current_time # Update last intervention time *when it starts*

        self.intervention_thread = threading.Thread(target=self._run_intervention_thread)
        self.intervention_thread.daemon = True
        self.intervention_thread.start()
        log_func(f"Intervention '{intervention_type}' (Tier {self._current_intervention_details['tier']}) initiated.")
        return True

    def stop_intervention(self):
        log_func = print
        if self.app and self.app.data_logger:
            log_func = self.app.data_logger.log_info

        if self.intervention_active and self.intervention_thread:
            log_func(f"Stopping intervention ('{self._current_intervention_details.get('type')}', Tier {self._current_intervention_details.get('tier')})...")
            self.intervention_active = False
        else:
            log_func("No active intervention to stop.")

    def notify_mode_change(self, new_mode, custom_message=None):
        """Handles speaking notifications for mode changes. These are not subject to feedback."""
        message = custom_message
        if not message:
            if new_mode == "paused": message = "Co-regulator paused."
            elif new_mode == "snoozed": message = f"Co-regulator snoozed for {config.SNOOZE_DURATION / 60:.0f} minutes."
            elif new_mode == "active": message = "Co-regulator active."
            elif new_mode == "error": message = "Sensor error detected. Operations affected."

        if message:
            self._speak(message)

    def register_feedback(self, feedback_value): # "helpful" or "unhelpful"
        if not self.last_feedback_eligible_intervention["timestamp"]:
            log_msg = "Feedback received, but no recent feedback-eligible intervention to link it to."
            if self.app and self.app.data_logger: self.app.data_logger.log_info(log_msg)
            else: print(log_msg)
            return

        time_since_intervention = time.time() - self.last_feedback_eligible_intervention["timestamp"]

        if time_since_intervention > self.feedback_window:
            log_msg = f"Feedback ('{feedback_value}') received for intervention '{self.last_feedback_eligible_intervention['message']}', but too late ({time_since_intervention:.1f}s > {self.feedback_window}s window)."
            if self.app and self.app.data_logger:
                self.app.data_logger.log_info(log_msg)
            else: print(log_msg)
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

        log_msg_console = f"Feedback '{feedback_value}' logged for intervention: '{self.last_feedback_eligible_intervention['message']}' (Type: {self.last_feedback_eligible_intervention['type']})"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_event(event_type="user_feedback", payload=feedback_payload)
            self.app.data_logger.log_info(log_msg_console)
        else:
            print(f"DataLogger not available. Feedback event: {feedback_payload}")
        print(log_msg_console)

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
    details_t1 = {"type": "posture_check", "message": "Sit straight!", "duration": 2}
    intervention_engine.start_intervention(details_t1)
    time.sleep(3)

    print("\n--- Test 2: Tier 2 Intervention ---")
    details_t2 = {"type": "calm_down", "message": "Feeling stressed? Try this sound.", "tier": 2, "duration": 3}
    intervention_engine.start_intervention(details_t2)
    time.sleep(4)

    print("\n--- Test 3: Tier 3 Intervention and stop early ---")
    details_t3 = {"type": "emergency_break", "message": "Mandatory break time!", "tier": 3, "duration": 5}
    intervention_engine.start_intervention(details_t3)
    time.sleep(1.5)
    intervention_engine.stop_intervention()
    time.sleep(1)

    print("\n--- Test 4: Start Intervention with missing type/message ---")
    intervention_engine.start_intervention({"message": "This will fail", "duration": 1})
    intervention_engine.start_intervention({"type": "fail_test", "duration": 1})
    time.sleep(0.5)

    print("\n--- Test 5: Attempt to start intervention while another is active ---")
    details_active = {"type": "break_reminder", "message": "Take a break!", "duration": 3}
    intervention_engine.start_intervention(details_active)
    time.sleep(0.5)
    details_ignored = {"type": "second_break", "message": "Seriously, break time!", "tier": 1, "duration": 3}
    intervention_engine.start_intervention(details_ignored) # Should be ignored
    time.sleep(3.5)

    print("\n--- Test 6: Intervention suppressed due to mode not 'active' ---")
    mock_logic_engine.set_mode("paused")
    details_paused = {"type": "posture_check_paused", "message": "Posture in pause?", "duration": 2}
    intervention_engine.start_intervention(details_paused)
    mock_logic_engine.set_mode("active")
    time.sleep(0.5)

    print("\n--- Test 7: Intervention suppressed due to MIN_TIME_BETWEEN_INTERVENTIONS ---")
    config.MIN_TIME_BETWEEN_INTERVENTIONS = 30
    intervention_engine.last_intervention_time = time.time() - 5
    details_too_soon = {"type": "too_soon_test", "message": "Am I too soon?", "duration": 2}
    intervention_engine.start_intervention(details_too_soon)
    time.sleep(0.5)
    config.MIN_TIME_BETWEEN_INTERVENTIONS = 10 # Reset for other tests


    print("\n--- Test 8: Feedback for a Tier 2 completed intervention ---")
    details_feedback = {"type": "feedback_test_tier2", "message": "Was this Tier 2 helpful?", "tier": 2, "duration": 1}
    intervention_engine.start_intervention(details_feedback)
    time.sleep(1.5)
    intervention_engine.register_feedback("helpful")
    time.sleep(0.5)

    print("\n--- Test 9: Mode Change Notification (separate from threaded interventions) ---")
    intervention_engine.notify_mode_change("snoozed")
    time.sleep(0.5)

    if intervention_engine.intervention_thread and intervention_engine.intervention_thread.is_alive():
        print("Waiting for active intervention thread to finish before exiting test...")
        intervention_engine.stop_intervention()
        intervention_engine.intervention_thread.join(timeout=2)

    print("\nInterventionEngine tests complete.")
