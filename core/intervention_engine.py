import time
import config
import datetime # For feedback timestamping
import threading
import pyttsx3 # For TTS

class InterventionEngine:
    def __init__(self, logic_engine, app_instance=None, data_logger_override=None):
        self.logic_engine = logic_engine
        self.app = app_instance
        self.data_logger = data_logger_override if data_logger_override else (self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None)

        self.last_intervention_time = 0 # For MIN_TIME_BETWEEN_INTERVENTIONS check
        self.intervention_active = False
        self.intervention_thread = None
        self._current_intervention_details = {} # Stores details of the currently active intervention

        self.last_feedback_eligible_intervention = {
            "message": None,
            "type": None,
            "timestamp": None
        }
        self.feedback_window = config.FEEDBACK_WINDOW_SECONDS if hasattr(config, 'FEEDBACK_WINDOW_SECONDS') else 15

        # TTS Engine Initialization
        self.tts_engine = None
        self.tts_enabled = getattr(config, 'ENABLE_TTS_OUTPUT', True)
        if self.tts_enabled:
            try:
                self.tts_engine = pyttsx3.init()
                current_rate = self.tts_engine.getProperty('rate')
                new_rate = getattr(config, 'TTS_RATE', 150) # Default to 150 if not in config
                self.tts_engine.setProperty('rate', new_rate)
                self._log_info(f"Set TTS rate to {new_rate} (was {current_rate}).")

                voices = self.tts_engine.getProperty('voices')
                desired_voice_id = getattr(config, 'TTS_VOICE_ID', None)

                if self.data_logger: # Check if logger exists before complex logging
                    self.data_logger.log_info("Available TTS voices:")
                    for voice in voices:
                        try:
                            self.data_logger.log_info(f"  ID: {voice.id}, Name: {voice.name}, Lang: {voice.languages}, Gender: {voice.gender}, Age: {voice.age}")
                        except Exception: # Some voice objects might not have all attributes
                            self.data_logger.log_info(f"  ID: {voice.id} (details partially unavailable)")


                if desired_voice_id:
                    found_voice = False
                    for voice in voices:
                        if voice.id == desired_voice_id:
                            self.tts_engine.setProperty('voice', desired_voice_id)
                            self._log_info(f"Successfully set TTS voice to ID: {desired_voice_id} (Name: {getattr(voice, 'name', 'N/A')})")
                            found_voice = True
                            break
                    if not found_voice:
                        self._log_warning(f"TTS_VOICE_ID '{desired_voice_id}' not found. Using default voice.")
                else:
                    self._log_info("No TTS_VOICE_ID specified. Using default voice.")

                try:
                    current_voice_id_prop = self.tts_engine.getProperty('voice')
                    current_voice_name = "Unknown"
                    for v in voices:
                        if v.id == current_voice_id_prop:
                            current_voice_name = getattr(v, 'name', 'N/A')
                            break
                    self._log_info(f"TTS engine initialized. Current voice ID: {current_voice_id_prop}, Name: '{current_voice_name}'. Rate: {self.tts_engine.getProperty('rate')}")
                except Exception as e_get_voice:
                     self._log_warning(f"Could not get current voice properties after init: {e_get_voice}")

            except Exception as e:
                self._log_error(f"Failed to initialize pyttsx3 TTS engine: {e}", details=str(e))
                self.tts_engine = None
                self.tts_enabled = False
        else:
            self._log_info("TTS output is disabled by configuration.")

        self._log_info("InterventionEngine initialized.")

    def _log_info(self, message):
        if self.data_logger: self.data_logger.log_info(f"InterventionEngine: {message}")
        else: print(f"INFO: InterventionEngine: {message}")

    def _log_warning(self, message):
        if self.data_logger: self.data_logger.log_warning(f"InterventionEngine: {message}")
        else: print(f"WARNING: InterventionEngine: {message}")

    def _log_error(self, message, details=""):
        if self.data_logger: self.data_logger.log_error(f"InterventionEngine: {message}", details=details)
        else: print(f"ERROR: InterventionEngine: {message} | Details: {details}")

    def _log_debug(self, message):
        if self.data_logger and hasattr(self.data_logger, 'log_debug'): self.data_logger.log_debug(f"InterventionEngine: {message}")
        elif self.data_logger: self.data_logger.log_info(f"InterventionEngine-DEBUG: {message}") # Fallback
        else: print(f"DEBUG: InterventionEngine: {message}")

    def _store_last_intervention(self, message, intervention_type_for_logging):
        self.last_feedback_eligible_intervention = {
            "message": message,
            "type": intervention_type_for_logging,
            "timestamp": time.time()
        }
        self._log_debug(f"Stored intervention for feedback: Type='{intervention_type_for_logging}', Msg='{message}'")

    def _speak(self, text):
        self._log_info(f"Attempting to speak: '{text}' (TTS Enabled: {self.tts_enabled})")
        if self.tts_enabled and self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self._log_info(f"Successfully spoke: '{text}'")
            except Exception as e:
                self._log_error(f"pyttsx3 engine error during say/runAndWait: {e}", details=str(e))
                print(f"SPEAKING (fallback due to TTS error): '{text}'") # Fallback to print
        else:
            print(f"SPEAKING (TTS disabled/unavailable): '{text}'") # Fallback to print

    def _play_sound(self, sound_file_path):
        self._log_info(f"Attempting to play sound: '{sound_file_path}' (Placeholder)")
        # Actual sound playing library would be used here

    def _show_visual_prompt(self, image_path_or_text):
        self._log_info(f"Attempting to show visual: '{image_path_or_text}' (Placeholder)")
        # Actual GUI toolkit would be used here

    def _run_intervention_thread(self):
        intervention_type = self._current_intervention_details.get("type", "unknown_intervention")
        message = self._current_intervention_details.get("message", "No message provided.")
        max_duration = self._current_intervention_details.get("duration", getattr(config, 'DEFAULT_INTERVENTION_DURATION', 10))
        tier = self._current_intervention_details.get("tier", 1)

        start_time = time.time()
        elapsed_time = 0
        log_prefix = f"Intervention (Type: {intervention_type}, Tier: {tier})"

        self._log_info(f"{log_prefix}: Started. Message: '{message}'. Max duration: {max_duration}s.")

        # Tier-based intervention execution
        if tier == 1:
            self._speak(message)
        elif tier == 2:
            self._speak(message)
            self._play_sound(self._current_intervention_details.get("sound_file", "path/to/tier2_calm_sound.wav"))
            self._log_info(f"{log_prefix}: Tier 2 action (e.g., sound) performed.")
        elif tier == 3:
            self._speak(f"Important: {message}")
            self._show_visual_prompt(self._current_intervention_details.get("visual_prompt", "Take a 5-minute break now."))
            self._log_info(f"{log_prefix}: Tier 3 action (e.g., visual prompt) performed.")
        else:
            self._speak(message)
            self._log_info(f"{log_prefix}: Executed default action for unknown tier {tier}.")

        if intervention_type not in ["mode_change_notification", "error_notification_spoken"]:
            self._store_last_intervention(message, intervention_type)

        current_app_mode = self.logic_engine.get_mode()
        if self.app and hasattr(self.app, 'tray_icon') and self.app.tray_icon:
            if intervention_type not in ["mode_change_notification"]:
                self._log_debug(f"{log_prefix}: Flashing tray icon.")
                flash_icon_type = "error" if "error" in intervention_type else "active"
                self.app.tray_icon.flash_icon(flash_status=flash_icon_type, original_status=current_app_mode)

        while self.intervention_active and elapsed_time < max_duration:
            time.sleep(0.1)
            elapsed_time = time.time() - start_time

        if not self.intervention_active:
            self._log_info(f"{log_prefix}: Stopped early by request.")
        elif elapsed_time >= max_duration:
            self._log_info(f"{log_prefix}: Completed (duration: {elapsed_time:.1f}s).")

        self.intervention_active = False
        self._current_intervention_details = {}

    def start_intervention(self, intervention_details):
        intervention_type = intervention_details.get("type")
        custom_message = intervention_details.get("message")

        if not intervention_type or not custom_message:
            self._log_error("Intervention attempt failed: 'type' and 'message' are required.")
            return False

        if self.intervention_active:
            self._log_info(f"Intervention attempt ignored: An intervention ('{self._current_intervention_details.get('type')}') is already active.")
            return False

        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            self._log_info(f"Intervention '{intervention_type}' suppressed: Mode is {current_app_mode}")
            return False

        current_time = time.time()
        min_time_between = getattr(config, 'MIN_TIME_BETWEEN_INTERVENTIONS', 300)
        if intervention_type not in ["mode_change_notification", "error_notification", "error_notification_spoken"] and \
           (current_time - self.last_intervention_time < min_time_between):
            self._log_info(f"Intervention '{intervention_type}' suppressed: Too soon since last intervention ({current_time - self.last_intervention_time:.1f}s < {min_time_between}s).")
            return False

        self.intervention_active = True
        self._current_intervention_details = {
            "type": intervention_type,
            "message": custom_message,
            "duration": intervention_details.get("duration", getattr(config, 'DEFAULT_INTERVENTION_DURATION', 10)),
            "tier": intervention_details.get("tier", 1),
            **{k: v for k, v in intervention_details.items() if k not in ["type", "message", "duration", "tier"]}
        }
        self.last_intervention_time = current_time

        self.intervention_thread = threading.Thread(target=self._run_intervention_thread)
        self.intervention_thread.daemon = True
        self.intervention_thread.start()
        self._log_info(f"Intervention '{intervention_type}' (Tier {self._current_intervention_details['tier']}) initiated.")
        return True

    def stop_intervention(self):
        if self.intervention_active and self.intervention_thread:
            self._log_info(f"Stopping intervention ('{self._current_intervention_details.get('type')}', Tier {self._current_intervention_details.get('tier')})...")
            self.intervention_active = False # Signal the thread to stop
        else:
            self._log_info("No active intervention to stop.")

    def notify_mode_change(self, new_mode, custom_message=None):
        message = custom_message
        if not message:
            snooze_duration_min = getattr(config, 'SNOOZE_DURATION', 3600) / 60
            if new_mode == "paused": message = "Co-regulator paused."
            elif new_mode == "snoozed": message = f"Co-regulator snoozed for {snooze_duration_min:.0f} minutes."
            elif new_mode == "active": message = "Co-regulator active."
            elif new_mode == "error": message = "Sensor error detected. Operations affected."

        if message:
            # These notifications should be immediate and not interfere with MIN_TIME_BETWEEN_INTERVENTIONS
            # They also don't run in a separate thread, as they are quick system status updates.
            self._speak(message)
            # Do not store these for feedback.

    def register_feedback(self, feedback_value):
        if not self.last_feedback_eligible_intervention["timestamp"]:
            self._log_info("Feedback received, but no recent feedback-eligible intervention to link it to.")
            return

        time_since_intervention = time.time() - self.last_feedback_eligible_intervention["timestamp"]

        if time_since_intervention > self.feedback_window:
            self._log_info(f"Feedback ('{feedback_value}') received for intervention '{self.last_feedback_eligible_intervention['message']}', but too late ({time_since_intervention:.1f}s > {self.feedback_window}s window).")
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
        if self.data_logger:
            self.data_logger.log_event(event_type="user_feedback", payload=feedback_payload)
            self.data_logger.log_info(log_msg_console)
        else:
            print(f"DataLogger not available. Feedback event: {feedback_payload}")
        print(log_msg_console) # Ensure it's printed for CLI testing

        self.last_feedback_eligible_intervention = {"message": None, "type": None, "timestamp": None}

if __name__ == '__main__':
    class MockDataLogger:
        def log_info(self, msg, details=""): print(f"MOCK_LOG_INFO: {msg}")
        def log_debug(self, msg, details=""): print(f"MOCK_LOG_DEBUG: {msg}")
        def log_warning(self, msg, details=""): print(f"MOCK_LOG_WARN: {msg}")
        def log_error(self, msg, details=""): print(f"MOCK_LOG_ERROR: {msg} | Details: {details}")
        def log_event(self, event_type, payload): print(f"MOCK_LOG_EVENT: Type='{event_type}', Payload='{payload}'")

    class MockLogicEngine:
        def __init__(self): self.mode = "active"
        def get_mode(self): return self.mode
        def set_mode(self, mode): self.mode = mode; print(f"MockLogicEngine: Mode set to {mode}")

    class MockTrayIcon:
        def flash_icon(self, flash_status, original_status): print(f"MOCK_TRAY_ICON: Flashing with '{flash_status}' from '{original_status}'.")

    class MockApp:
        def __init__(self):
            self.tray_icon = MockTrayIcon()
            self.data_logger = MockDataLogger() # Use the mock logger
            # Ensure config attributes are present for tests
            if not hasattr(config, 'FEEDBACK_WINDOW_SECONDS'): config.FEEDBACK_WINDOW_SECONDS = 15
            if not hasattr(config, 'MIN_TIME_BETWEEN_INTERVENTIONS'): config.MIN_TIME_BETWEEN_INTERVENTIONS = 2 # Short for testing
            if not hasattr(config, 'DEFAULT_INTERVENTION_DURATION'): config.DEFAULT_INTERVENTION_DURATION = 3 # Short for testing
            print("MockApp for InterventionEngine test created.")

    mock_logic_engine = MockLogicEngine()
    mock_app_instance = MockApp()

    # Pass the mock_data_logger directly for robust logging in tests
    intervention_engine = InterventionEngine(mock_logic_engine, mock_app_instance, data_logger_override=mock_app_instance.data_logger)

    print(f"\n--- TTS Engine Status: {'Enabled' if intervention_engine.tts_enabled else 'Disabled'} ---")
    if intervention_engine.tts_engine is None and intervention_engine.tts_enabled:
        print("WARN: TTS was enabled but engine failed to initialize. Check pyttsx3 dependencies (espeak, nsss, sapi5).")
    elif intervention_engine.tts_engine:
        print("--- Available Voices (for testing configuration) ---")
        voices = intervention_engine.tts_engine.getProperty('voices')
        for i, voice in enumerate(voices):
            try:
                print(f"  Voice {i}: ID: {voice.id}, Name: {voice.name}, Lang: {voice.languages}")
            except:
                print(f"  Voice {i}: ID: {voice.id} (details partially unavailable)")

        print(f"Current Rate: {intervention_engine.tts_engine.getProperty('rate')}")
        try:
            current_voice_id = intervention_engine.tts_engine.getProperty('voice')
            current_voice_name = "Unknown"
            for v in voices:
                if v.id == current_voice_id:
                    current_voice_name = getattr(v, 'name', 'N/A')
                    break
            print(f"Currently Used Voice ID: {current_voice_id} (Name: {current_voice_name})")
        except Exception as e:
            print(f"Could not get current voice details from pyttsx3: {e}")
        print("----------------------------------------------------")

    print("\n--- Test 1: Tier 1 Intervention (Default) ---")
    details_t1 = {"type": "posture_check", "message": "Sit straight!", "duration": 1} # Shorter duration for test
    intervention_engine.start_intervention(details_t1)
    time.sleep(1.5) # Wait for it to complete

    print("\n--- Test 2: Tier 2 Intervention ---")
    details_t2 = {"type": "calm_down", "message": "Feeling stressed? Try this sound.", "tier": 2, "duration": 1.5}
    intervention_engine.start_intervention(details_t2)
    time.sleep(2)

    print("\n--- Test 3: Tier 3 Intervention and stop early ---")
    details_t3 = {"type": "emergency_break", "message": "Mandatory break time!", "tier": 3, "duration": 3}
    intervention_engine.start_intervention(details_t3)
    time.sleep(1)
    intervention_engine.stop_intervention()
    time.sleep(0.5) # Allow thread to acknowledge stop

    print("\n--- Test 4: Start Intervention with missing type/message ---")
    intervention_engine.start_intervention({"message": "This will fail", "duration": 1})
    intervention_engine.start_intervention({"type": "fail_test", "duration": 1})
    time.sleep(0.5)

    print("\n--- Test 5: Attempt to start intervention while another is active ---")
    details_active = {"type": "break_reminder", "message": "Take a break!", "duration": 1.5}
    intervention_engine.start_intervention(details_active)
    time.sleep(0.1) # Let it start
    details_ignored = {"type": "second_break", "message": "Seriously, break time!", "tier": 1, "duration": 1}
    intervention_engine.start_intervention(details_ignored) # Should be ignored
    time.sleep(2) # Wait for first one to finish

    print("\n--- Test 6: Intervention suppressed due to mode not 'active' ---")
    mock_logic_engine.set_mode("paused")
    details_paused = {"type": "posture_check_paused", "message": "Posture in pause?", "duration": 1}
    intervention_engine.start_intervention(details_paused)
    mock_logic_engine.set_mode("active") # Reset for next tests
    time.sleep(0.5)

    print("\n--- Test 7: Intervention suppressed due to MIN_TIME_BETWEEN_INTERVENTIONS ---")
    # First, ensure one intervention runs to set last_intervention_time
    intervention_engine.start_intervention({"type":"first_one", "message":"First one for timing.", "duration":0.5})
    time.sleep(0.6) # Let it finish
    # Now try to trigger another one too soon
    details_too_soon = {"type": "too_soon_test", "message": "Am I too soon?", "duration": 1}
    intervention_engine.start_intervention(details_too_soon) # Should be suppressed by default MIN_TIME_BETWEEN_INTERVENTIONS
    time.sleep(0.5)


    print("\n--- Test 8: Feedback for a Tier 2 completed intervention ---")
    details_feedback = {"type": "feedback_test_tier2", "message": "Was this Tier 2 helpful?", "tier": 2, "duration": 0.5}
    intervention_engine.start_intervention(details_feedback)
    time.sleep(1) # Let it complete
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
