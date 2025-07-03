import time
import config
from .data_logger import DataLogger # Assuming DataLogger is in the same directory

class LogicEngine:
    def __init__(self, audio_sensor=None, video_sensor=None, logger=None):
        self.current_mode = config.DEFAULT_MODE
        self.snooze_end_time = 0
        self.previous_mode_before_pause = config.DEFAULT_MODE
        self.tray_callback = None # Callback for notifying tray/main app
        self.audio_sensor = audio_sensor
        self.video_sensor = video_sensor
        self.logger = logger if logger else DataLogger() # Use provided logger or create one

        self.logger.log_info(f"LogicEngine initialized. Mode: {self.current_mode}")

    def get_mode(self):
        old_mode = self.current_mode
        if self.current_mode == "snoozed":
            if time.time() >= self.snooze_end_time and self.snooze_end_time != 0:
                self.logger.log_info("Snooze expired.")
                self.snooze_end_time = 0 # Reset snooze time
                self.set_mode("active", from_snooze_expiry=True)
                # set_mode will call _notify_mode_change

        # If mode was changed by snooze expiry, self.current_mode is now updated.
        # If not, it's the same as old_mode.
        return self.current_mode

    def set_mode(self, mode, from_snooze_expiry=False):
        if mode not in ["active", "snoozed", "paused", "error"]: # Added error mode
            self.logger.log_warning(f"Attempted to set invalid mode: {mode}")
            return

        old_mode = self.current_mode
        if mode == old_mode and not from_snooze_expiry : # Allow re-setting active if snooze expired
            # (e.g. if already active, but snooze expired, we still want notification)
            # This condition might need refinement based on desired notification behavior
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
            # If mode becomes active (either by user or snooze expiry), ensure snooze_end_time is cleared
            self.snooze_end_time = 0

        self._notify_mode_change(old_mode, new_mode=self.current_mode, from_snooze_expiry=from_snooze_expiry)

    def cycle_mode(self):
        current_actual_mode = self.get_mode()
        if current_actual_mode == "active":
            self.set_mode("snoozed")
        elif current_actual_mode == "snoozed":
            self.set_mode("paused")
        elif current_actual_mode == "paused":
            # When cycling from paused, go to active, not previous_mode_before_pause
            self.set_mode("active")

    def toggle_pause_resume(self):
        current_actual_mode = self.get_mode()
        if current_actual_mode == "paused":
            # If snooze would have expired while paused, return to active.
            if self.previous_mode_before_pause == "snoozed" and \
               self.snooze_end_time != 0 and time.time() >= self.snooze_end_time:
                self.snooze_end_time = 0 # Clear snooze as it's now handled
                self.set_mode("active")
            else:
                self.set_mode(self.previous_mode_before_pause)
        else:
            # This will set self.previous_mode_before_pause correctly if current is not "paused"
            self.set_mode("paused")

    def _notify_mode_change(self, old_mode, new_mode, from_snooze_expiry=False):
        self.logger.log_info(f"LogicEngine Notification: Mode changed from {old_mode} to {new_mode}{' (due to snooze expiry)' if from_snooze_expiry else ''}")
        if self.tray_callback:
            # Pass both old and new mode for more context if needed by callback
            self.tray_callback(new_mode=new_mode, old_mode=old_mode)

    def update(self):
        """
        Periodically called to update the logic engine's state and evaluations.
        For now, primarily ensures snooze expiry is checked.
        """
        # This call will automatically transition from "snoozed" to "active"
        # if the snooze timer has expired, and notify via tray_callback.
        current_mode = self.get_mode() # Ensures mode is up-to-date

        self.logger.log_debug(f"LogicEngine update. Current mode: {current_mode}")

        # Placeholder for sensor interaction
        if self.audio_sensor:
            try:
                audio_level = self.audio_sensor.get_level() # Assuming this method will exist
                self.logger.log_debug(f"Audio level: {audio_level}")
            except AttributeError:
                self.logger.log_warning("audio_sensor does not have get_level method or sensor not available.")
            except Exception as e:
                self.logger.log_error(f"Error getting audio level: {e}")


        if self.video_sensor:
            try:
                video_activity = self.video_sensor.get_activity_level() # Assuming this method will exist
                self.logger.log_debug(f"Video activity: {video_activity}")
            except AttributeError:
                self.logger.log_warning("video_sensor does not have get_activity_level method or sensor not available.")
            except Exception as e:
                self.logger.log_error(f"Error getting video activity: {e}")

        # Mode-Driven Behavior Conceptual Outline
        if current_mode == "active":
            self.logger.log_debug("LogicEngine: Mode is ACTIVE. Evaluating conditions...")
            # TODO: Implement logic for active mode:
            # 1. Process sensor data (e.g., audio_level, video_activity).
            # 2. If conditions warrant, consult LMM.
            # 3. Based on LMM response or rules, decide if an intervention is needed.
            # 4. Trigger intervention via InterventionEngine (to be integrated).
            # 5. Potentially change mode (e.g., to "error" if a sensor fails critically).
            pass
        elif current_mode == "snoozed":
            self.logger.log_debug("LogicEngine: Mode is SNOOZED. Minimal processing.")
            # TODO: Snooze specific logic, if any (e.g. light monitoring without intervention)
            pass
        elif current_mode == "paused":
            self.logger.log_debug("LogicEngine: Mode is PAUSED. No active processing.")
            # TODO: Paused specific logic, if any.
            pass
        elif current_mode == "error":
            self.logger.log_debug("LogicEngine: Mode is ERROR. Attempting to handle or log.")
            # TODO: Error handling logic:
            # 1. Log detailed error information.
            # 2. Attempt recovery if possible.
            # 3. Notify user of persistent error state.
            pass


if __name__ == '__main__':
    # Mock sensor classes for testing
    class MockSensor:
        def __init__(self, name="mock"):
            self.name = name
        def get_level(self):
            return f"{self.name}_level_data"
        def get_activity_level(self):
            return f"{self.name}_activity_data"

    mock_audio = MockSensor("audio")
    mock_video = MockSensor("video")

    # Assuming DataLogger is in the same directory or properly pathed
    # For testing, let's ensure config has defaults if not present
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "test_logic_engine_log.txt"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"

    logger = DataLogger(log_file_path=config.LOG_FILE) # Use a specific logger for the test output

    engine = LogicEngine(audio_sensor=mock_audio, video_sensor=mock_video, logger=logger)

    # Mock callback for testing
    def test_callback(new_mode, old_mode):
        print(f"Test Callback: Mode changed from {old_mode} to {new_mode}")
    engine.tray_callback = test_callback

    print(f"Initial mode: {engine.get_mode()}") # active
    engine.update() # Call update to test sensor logging

    engine.cycle_mode() # active -> snoozed
    print(f"Mode after cycle 1: {engine.get_mode()}") # snoozed
    engine.update() # Call update

    engine.toggle_pause_resume() # snoozed -> paused
    print(f"Mode after pause: {engine.get_mode()}") # paused
    engine.update() # Call update

    engine.toggle_pause_resume() # paused -> snoozed (restores previous_mode_before_pause)
    print(f"Mode after resume: {engine.get_mode()}") # snoozed
    engine.update() # Call update

    print("\nSimulating snooze duration passing...")
    engine.snooze_end_time = time.time() - 1 # Force snooze to expire
    # get_mode() is called by update(), which will trigger the change and notification
    engine.update()
    print(f"Mode after snooze expired (after update call): {engine.get_mode()}")
    assert engine.current_mode == "active"

    print("\nTesting pause then snooze expiry while paused then resume...")
    engine.set_mode("active") # Reset to active
    engine.set_mode("snoozed") # snoozed
    engine.snooze_end_time = time.time() + 5 # Snooze for 5 seconds
    print(f"Snoozing for 5s. Current mode: {engine.get_mode()}")
    engine.set_mode("paused") # paused (while snoozing)
    print(f"Paused. Current mode: {engine.get_mode()}")
    print("Waiting for 6 seconds to ensure snooze expires...")
    time.sleep(6)
    # Snooze has now expired. previous_mode_before_pause is "snoozed".
    # snooze_end_time is in the past.
    engine.toggle_pause_resume() # paused -> active (because snooze expired)
    print(f"Mode after resuming from pause (snooze should have expired): {engine.get_mode()}")
    assert engine.current_mode == "active"

    engine.set_mode("active")
    engine.cycle_mode() # active -> snoozed
    engine.cycle_mode() # snoozed -> paused
    engine.cycle_mode() # paused -> active
    print(f"Mode after 3 cycles: {engine.get_mode()}")
    assert engine.current_mode == "active"
    print("LogicEngine tests complete.")
