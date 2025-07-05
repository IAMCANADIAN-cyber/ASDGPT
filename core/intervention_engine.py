import time
import config
import datetime # For feedback timestamping

class InterventionEngine:
    def __init__(self, logic_engine, app_instance=None):
        self.logic_engine = logic_engine
        self.app = app_instance # Used for DataLogger and TrayIcon
        self.last_intervention_time = 0

        # Store details of the last intervention that is eligible for feedback
        self.last_feedback_eligible_intervention = {
            "message": None,
            "type": None, # The specific type of intervention, e.g., "slumped_posture_alert"
            "timestamp": None
        }
        self.feedback_window = config.FEEDBACK_WINDOW_SECONDS if hasattr(config, 'FEEDBACK_WINDOW_SECONDS') else 15

        if self.app and hasattr(self.app, 'data_logger'):
            self.app.data_logger.log_info("InterventionEngine initialized.")
        else:
            print("InterventionEngine initialized (DataLogger not available).")

    def _store_last_intervention(self, message, intervention_type_for_logging):
        """Stores details of an intervention that qualifies for feedback."""
        self.last_feedback_eligible_intervention = {
            "message": message,
            "type": intervention_type_for_logging,
            "timestamp": time.time()
        }
        if self.app and self.app.data_logger:
             self.app.data_logger.log_debug(f"Stored intervention for feedback: Type='{intervention_type_for_logging}', Msg='{message}'")


    def provide_intervention(self, intervention_type, custom_message=""):
        # intervention_type: Broad category like "custom", "posture_alert", "break_reminder"
        # custom_message: The actual text to be spoken, or a template key

        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            if self.app and self.app.data_logger: self.app.data_logger.log_debug(f"Intervention suppressed: Mode is {current_app_mode}")
            return

        current_time = time.time()
        # Mode change notifications (handled by notify_mode_change) and error notifications bypass this time limit.
        # Regular proactive interventions adhere to the MIN_TIME_BETWEEN_INTERVENTIONS.
        if intervention_type not in ["mode_change_notification", "error_notification"] and \
           (current_time - self.last_intervention_time < config.MIN_TIME_BETWEEN_INTERVENTIONS):
            if self.app and self.app.data_logger: self.app.data_logger.log_debug(f"Intervention suppressed: Too soon since last intervention.")
            return

        message_to_speak = custom_message # Default to custom_message
        intervention_type_for_logging = intervention_type # This is what gets logged as the "type"

        # Example: if intervention_type is "posture_alert" and custom_message is empty,
        # you might look up a predefined message. For now, custom_message is expected to be populated.
        if not message_to_speak:
            message_to_speak = f"A generic {intervention_type} was triggered." # Fallback

        if message_to_speak:
            self._speak(message_to_speak)
            self.last_intervention_time = current_time

            # Store details for potential feedback, ONLY for actual user-facing proactive interventions.
            # Do not store for mode changes or simple error popups unless feedback on those is desired.
            # Let's assume "custom" type interventions are things user might want to give feedback on.
            # Also specific types like "slumped_posture_alert" etc. would be stored.
            if intervention_type not in ["mode_change_notification", "error_notification_spoken"]: # Don't solicit feedback for these
                 self._store_last_intervention(message_to_speak, intervention_type_for_logging)

            # Flash tray icon
            if self.app and hasattr(self.app, 'tray_icon') and self.app.tray_icon:
                # Avoid flashing if the intervention IS a mode change announcement,
                # as the icon will be updated permanently anyway.
                if intervention_type not in ["mode_change_notification"]: # Flash for errors and other interventions
                    if self.app.data_logger: self.app.data_logger.log_debug("InterventionEngine: Flashing tray icon for intervention.")
                    flash_icon_type = "error" if "error" in intervention_type else "active"
                    self.app.tray_icon.flash_icon(flash_status=flash_icon_type, original_status=current_app_mode)


import pyttsx3 # Import pyttsx3

class InterventionEngine:
    def __init__(self, logic_engine, app_instance=None, data_logger_override=None): # Added data_logger_override for testing
        self.logic_engine = logic_engine
        self.app = app_instance
        self.data_logger = data_logger_override if data_logger_override else (self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None)
        self.last_intervention_time = 0

        # Store details of the last intervention that is eligible for feedback
        self.last_feedback_eligible_intervention = {
            "message": None,
            "type": None,
            "timestamp": None
        }
        self.feedback_window = config.FEEDBACK_WINDOW_SECONDS if hasattr(config, 'FEEDBACK_WINDOW_SECONDS') else 15

        # TTS Engine Initialization
        self.tts_engine = None
        self.tts_enabled = getattr(config, 'ENABLE_TTS_OUTPUT', True) # Default to True if not in config
        if self.tts_enabled:
            try:
                self.tts_engine = pyttsx3.init()
                # Configure voice, rate, volume
                current_rate = self.tts_engine.getProperty('rate')
                new_rate = getattr(config, 'TTS_RATE', current_rate) # Default to current if not in config
                if new_rate != current_rate:
                    self.tts_engine.setProperty('rate', new_rate)
                    if self.data_logger: self.data_logger.log_info(f"Set TTS rate to {new_rate}.")
                else: # Default is often 200, 150 is a bit slower. Let's set a default if not specified.
                    self.tts_engine.setProperty('rate', 150)
                    if self.data_logger: self.data_logger.log_info(f"Set TTS rate to default 150 (was {current_rate}).")


                voices = self.tts_engine.getProperty('voices')
                desired_voice_id = getattr(config, 'TTS_VOICE_ID', None)

                if self.data_logger:
                    self.data_logger.log_info("Available TTS voices:")
                    for voice in voices:
                        self.data_logger.log_info(f"  ID: {voice.id}, Name: {voice.name}, Lang: {voice.languages}, Gender: {voice.gender}, Age: {voice.age}")

                if desired_voice_id:
                    found_voice = False
                    for voice in voices:
                        if voice.id == desired_voice_id:
                            self.tts_engine.setProperty('voice', desired_voice_id)
                            if self.data_logger: self.data_logger.log_info(f"Successfully set TTS voice to ID: {desired_voice_id} (Name: {voice.name})")
                            found_voice = True
                            break
                    if not found_voice:
                        if self.data_logger: self.data_logger.log_warning(f"TTS_VOICE_ID '{desired_voice_id}' not found. Using default voice.")
                else:
                    if self.data_logger: self.data_logger.log_info("No TTS_VOICE_ID specified. Using default voice.")

                # Log the voice being used if possible (after setting)
                try:
                    current_voice = self.tts_engine.getProperty('voice')
                    # Find name of current_voice.id in voices list
                    current_voice_name = "Unknown (could not get name)"
                    for v in voices:
                        if v.id == current_voice:
                            current_voice_name = v.name
                            break
                    if self.data_logger: self.data_logger.log_info(f"TTS engine initialized. Current voice: ID={current_voice}, Name='{current_voice_name}'. Rate: {self.tts_engine.getProperty('rate')}")
                except Exception as e_get_voice: # Some engines might error here if voice not set properly
                     if self.data_logger: self.data_logger.log_warning(f"Could not get current voice properties after init: {e_get_voice}")

            except Exception as e:
                if self.data_logger: self.data_logger.log_error(f"Failed to initialize pyttsx3 TTS engine: {e}", details=str(e))
                else: print(f"ERROR: Failed to initialize pyttsx3 TTS engine: {e}")
                self.tts_engine = None # Ensure it's None if init fails
                self.tts_enabled = False # Disable TTS if engine failed
        else:
            if self.data_logger: self.data_logger.log_info("TTS output is disabled by configuration.")
            else: print("INFO: TTS output is disabled by configuration.")


        if self.data_logger:
            self.data_logger.log_info("InterventionEngine initialized.")
        else:
            print("InterventionEngine initialized (DataLogger not available for main init message).")

    def _log_info(self, message):
        if self.data_logger: self.data_logger.log_info(f"InterventionEngine: {message}")
        else: print(f"INFO: InterventionEngine: {message}")

    def _log_debug(self, message):
        if self.data_logger and hasattr(self.data_logger, 'log_debug'): self.data_logger.log_debug(f"InterventionEngine: {message}")
        elif self.data_logger : self.data_logger.log_info(f"InterventionEngine-DEBUG: {message}") # Fallback
        else: print(f"DEBUG: InterventionEngine: {message}")

    def _store_last_intervention(self, message, intervention_type_for_logging):
        """Stores details of an intervention that qualifies for feedback."""
        self.last_feedback_eligible_intervention = {
            "message": message,
            "type": intervention_type_for_logging,
            "timestamp": time.time()
        }
        self._log_debug(f"Stored intervention for feedback: Type='{intervention_type_for_logging}', Msg='{message}'")


    def provide_intervention(self, intervention_type, custom_message=""):
        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            self._log_debug(f"Intervention suppressed: Mode is {current_app_mode}")
            return

        current_time = time.time()
        if intervention_type not in ["mode_change_notification", "error_notification"] and \
           (current_time - self.last_intervention_time < config.MIN_TIME_BETWEEN_INTERVENTIONS):
            self._log_debug(f"Intervention suppressed: Too soon since last intervention.")
            return

        message_to_speak = custom_message
        intervention_type_for_logging = intervention_type

        if not message_to_speak:
            message_to_speak = f"A generic {intervention_type} was triggered."

        if message_to_speak:
            self._speak(message_to_speak)
            self.last_intervention_time = current_time

            if intervention_type not in ["mode_change_notification", "error_notification_spoken"]:
                 self._store_last_intervention(message_to_speak, intervention_type_for_logging)

            if self.app and hasattr(self.app, 'tray_icon') and self.app.tray_icon:
                if intervention_type not in ["mode_change_notification"]:
                    self._log_debug("Flashing tray icon for intervention.")
                    flash_icon_type = "error" if "error" in intervention_type else "active"
                    self.app.tray_icon.flash_icon(flash_status=flash_icon_type, original_status=current_app_mode)


    def _speak(self, text):
        self._log_info(f"Attempting to speak: '{text}' (TTS Enabled: {self.tts_enabled})")
        if self.tts_enabled and self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self._log_info(f"Successfully spoke: '{text}'")
            except Exception as e:
                log_msg = f"pyttsx3 engine error during say/runAndWait: {e}"
                if self.data_logger: self.data_logger.log_error(log_msg, details=str(e))
                else: print(f"ERROR: {log_msg}")
                # Fallback to print if TTS fails mid-operation
                print(f"SPEAKING (fallback due to TTS error): '{text}'")
        else:
            # Fallback to print if TTS is disabled or engine not initialized
            print(f"SPEAKING (TTS disabled/unavailable): '{text}'")


    def notify_mode_change(self, new_mode, custom_message=None):
        """Handles speaking notifications for mode changes. These are not subject to feedback."""
        message = custom_message
        if not message: # Generate default message if none provided
            if new_mode == "paused": message = "Co-regulator paused."
            elif new_mode == "snoozed": message = f"Co-regulator snoozed for {config.SNOOZE_DURATION / 60:.0f} minutes."
            elif new_mode == "active": message = "Co-regulator active."
            elif new_mode == "error": message = "Sensor error detected. Operations affected." # Specific message for error state

        if message:
            # These are system status messages, not "interventions" in the feedback sense.
            # Bypass MIN_TIME_BETWEEN_INTERVENTIONS and don't store for feedback.
            original_last_intervention_time = self.last_intervention_time
            self.last_intervention_time = 0 # Temporarily allow this to speak
            self._speak(message)
            self.last_intervention_time = original_last_intervention_time # Restore
            # Do NOT call _store_last_intervention for these.

            # Tray icon will be updated by main.py or LogicEngine callback. No flash needed here.

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
                # Optionally, still log it as an event but mark as "late"
                # self.app.data_logger.log_event("user_feedback_late", {...})
            else: print(log_msg)
            # Clear the intervention so it can't be late-feedbacked again
            self.last_feedback_eligible_intervention = {"message": None, "type": None, "timestamp": None}
            return

        feedback_payload = {
            "intervention_message": self.last_feedback_eligible_intervention["message"],
            "intervention_type": self.last_feedback_eligible_intervention["type"], # The specific type stored
            "feedback_value": feedback_value,
            "timestamp_of_intervention": datetime.datetime.fromtimestamp(self.last_feedback_eligible_intervention["timestamp"]).isoformat(),
            "timestamp_of_feedback": datetime.datetime.now().isoformat(),
            "time_delta_seconds": round(time_since_intervention, 2)
        }

        log_msg_console = f"Feedback '{feedback_value}' logged for intervention: '{self.last_feedback_eligible_intervention['message']}' (Type: {self.last_feedback_eligible_intervention['type']})"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_event(event_type="user_feedback", payload=feedback_payload)
            self.app.data_logger.log_info(log_msg_console) # Also log to main log for context
        else:
            print(f"DataLogger not available. Feedback event: {feedback_payload}")
        print(log_msg_console) # Ensure it's printed for CLI testing

        # Clear last intervention after successful feedback to prevent multiple feedbacks for the same event.
        self.last_feedback_eligible_intervention = {"message": None, "type": None, "timestamp": None}


if __name__ == '__main__':
    # Enhanced MockApp for testing feedback logging
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

    class MockApp:
        def __init__(self):
            self.tray_icon = None
            self.data_logger = MockDataLogger()
            if not hasattr(config, 'FEEDBACK_WINDOW_SECONDS'): # Ensure config attr for test
                config.FEEDBACK_WINDOW_SECONDS = 15
            print("MockApp for InterventionEngine test created with MockDataLogger.")

    mock_logic_engine = MockLogicEngine()
    mock_app_instance = MockApp() # This will use the MockDataLogger defined above

    # For testing, explicitly pass the mock_logger to InterventionEngine
    # as self.app.data_logger might not be set up exactly as in the real app instance.
    intervention_engine = InterventionEngine(mock_logic_engine, mock_app_instance, data_logger_override=mock_app_instance.data_logger)

    # Test TTS enabled/disabled
    print(f"\n--- TTS Engine Status: {'Enabled' if intervention_engine.tts_enabled else 'Disabled'} ---")
    if intervention_engine.tts_engine is None and intervention_engine.tts_enabled:
        print("WARN: TTS was enabled but engine failed to initialize. Check pyttsx3 dependencies (espeak, nsss, sapi5).")
    elif intervention_engine.tts_engine:
        # List voices for test context
        print("--- Available Voices (for testing configuration) ---")
        voices = intervention_engine.tts_engine.getProperty('voices')
        for voice in voices:
            print(f"  ID: {voice.id}, Name: {voice.name}, Lang: {voice.languages}")
        print(f"Current Rate: {intervention_engine.tts_engine.getProperty('rate')}")
        current_voice_id = intervention_engine.tts_engine.getProperty('voice')
        current_voice_name = "Unknown"
        for v in voices:
            if v.id == current_voice_id:
                current_voice_name = v.name
                break
        print(f"Currently Used Voice ID: {current_voice_id} (Name: {current_voice_name})")
        print("----------------------------------------------------")


    print("\n--- Testing Intervention and Immediate Feedback (TTS output expected if enabled) ---")
    # Simulate a specific type of intervention
    intervention_engine.provide_intervention("posture_check", "Remember to sit straight!")
    print("Simulating user pressing 'helpful' (Ctrl+Alt+Up) almost immediately...")
    intervention_engine.register_feedback("helpful")

    print("\n--- Testing Feedback Window Expiry ---")
    intervention_engine.provide_intervention("hydration_reminder", "Time for some water?")
    print(f"Waiting for {intervention_engine.feedback_window + 1} seconds (which is > feedback window of {intervention_engine.feedback_window}s)...")
    time.sleep(intervention_engine.feedback_window + 1)
    print("Simulating user pressing 'unhelpful' (Ctrl+Alt+Down) too late...")
    intervention_engine.register_feedback("unhelpful")

    print("\n--- Testing Feedback with No Prior Eligible Intervention ---")
    # Manually clear the last eligible intervention for this test case
    intervention_engine.last_feedback_eligible_intervention = {"message": None, "type": None, "timestamp": None}
    print("Simulating user pressing 'helpful' when no intervention is eligible for feedback...")
    intervention_engine.register_feedback("helpful")

    print("\n--- Testing Mode Change Notifications (Not Eligible for Feedback via this system) ---")
    intervention_engine.notify_mode_change("paused", "System is now paused by user.")
    print("Simulating user pressing 'helpful' after a mode change notification...")
    intervention_engine.register_feedback("helpful") # Should state no eligible intervention

    print("\n--- Testing Intervention, then another, then feedback for the LATEST one ---")
    intervention_engine.provide_intervention("screen_break_suggestion", "Look away from the screen for 20 seconds.")
    time.sleep(1) # Small delay
    intervention_engine.provide_intervention("custom_task_focus", "Focus on your current task.")
    print("Simulating user pressing 'unhelpful' for the 'focus on task' intervention...")
    intervention_engine.register_feedback("unhelpful")


    print("\nInterventionEngine tests complete.")
