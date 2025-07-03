import time
import config
import datetime # For feedback timestamping
import random # For selecting from multiple prompts

# --- Placeholder Intervention Details ---
INTERVENTION_TYPES = {
    "FATIGUE_BREAK": "fatigue_break_suggestion",
    "STRESS_BREATHING": "stress_breathing_exercise_suggestion",
    "GENERIC_PROMPT": "generic_lmm_prompt" # For future LMM integration
}

FATIGUE_PROMPTS = [
    "You seem to be tiring. How about a 5-minute break to refresh?",
    "Feeling a bit fatigued? A short walk or some stretches might help.",
    "This might be a good time to step away and rest your eyes for a few minutes."
]

STRESS_PROMPTS = [
    "Feeling stressed? Let's try a quick breathing exercise. Inhale for 4, hold for 4, exhale for 6.",
    "Signs of stress detected. Would you like to do a 1-minute mindfulness exercise?",
    "If you're feeling overwhelmed, a brief pause and some deep breaths can make a difference."
]
# --- End Placeholder Intervention Details ---

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

    def decide_intervention(self, sensor_data: dict) -> tuple[str | None, str | None]:
        """
        Decides if an intervention is needed based on sensor data and context.
        Returns: (intervention_type_for_logging, message_to_speak) or (None, None)
        """
        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            # self.app.data_logger.log_debug("DecideIntervention: Suppressed, Mode is not active.") # Optional, can be noisy
            return None, None

        current_time = time.time()
        if (current_time - self.last_intervention_time < config.MIN_TIME_BETWEEN_INTERVENTIONS):
            # self.app.data_logger.log_debug("DecideIntervention: Suppressed, too soon since last intervention.") # Optional
            return None, None

        # Basic rules based on sensor_data
        video_emotion = sensor_data.get("video_emotion")
        audio_emotion = sensor_data.get("audio_emotion")
        # time_of_day_segment = sensor_data.get("time_of_day_segment") # Example for future use

        intervention_type_to_log = None
        message_to_speak = None

        # Rule 1: Fatigue detected by video
        if video_emotion == "fatigue detected":
            self.app.data_logger.log_info(f"DecideIntervention: Condition met for fatigue (video: {video_emotion}).")
            intervention_type_to_log = INTERVENTION_TYPES["FATIGUE_BREAK"]
            message_to_speak = random.choice(FATIGUE_PROMPTS)
            # Potentially add more conditions like time_of_day_segment == "afternoon"

        # Rule 2: Stress detected by audio (can add more complex logic, e.g., if fatigue not already triggered)
        elif audio_emotion == "stress detected": # Use elif to avoid multiple triggers in one cycle for now
            self.app.data_logger.log_info(f"DecideIntervention: Condition met for stress (audio: {audio_emotion}).")
            intervention_type_to_log = INTERVENTION_TYPES["STRESS_BREATHING"]
            message_to_speak = random.choice(STRESS_PROMPTS)

        # Add more rules here in the future, potentially involving LMM calls

        if intervention_type_to_log and message_to_speak:
            # self.last_intervention_time = current_time # This will be set by provide_intervention
            return intervention_type_to_log, message_to_speak

        return None, None

    def provide_intervention(self, intervention_type, custom_message=""):
        # intervention_type: Broad category like "custom", "posture_alert", "break_reminder"
        # custom_message: The actual text to be spoken, or a template key

        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            if self.app and self.app.data_logger: self.app.data_logger.log_debug(f"ProvideIntervention: Suppressed, Mode is {current_app_mode}")
            return

        # Timing check for proactive interventions (those not in the list below) is now primarily handled by `decide_intervention`.
        # `provide_intervention` will proceed if called for such types, assuming timing is okay.
        # It will still update self.last_intervention_time for all spoken interventions except mode changes handled by notify_mode_change.
        # Error notifications will also update last_intervention_time if they are spoken via this method.
        # Mode changes via notify_mode_change have their own timing logic (bypass MIN_TIME_BETWEEN_INTERVENTIONS).

        # The explicit check for MIN_TIME_BETWEEN_INTERVENTIONS is removed here for proactive types,
        # as decide_intervention should be the gatekeeper.
        # However, we still need to set self.last_intervention_time correctly.

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


    def _speak(self, text):
        # Placeholder for actual text-to-speech (TTS) implementation
        if self.app and self.app.data_logger: self.app.data_logger.log_info(f"SPEAKING: '{text}'")
        else: print(f"SPEAKING: '{text}'")
        # Actual TTS would go here

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
    mock_app_instance = MockApp()
    intervention_engine = InterventionEngine(mock_logic_engine, mock_app_instance)

    print("\n--- Testing Intervention and Immediate Feedback ---")
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
