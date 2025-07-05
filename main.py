import time
import keyboard
import config
from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine
from core.system_tray import ACRTrayIcon
from core.data_logger import DataLogger
from core.lmm_interface import LMMInterface # Added LMMInterface import
from sensors.video_sensor import VideoSensor
# AudioSensor is initialized within LogicEngine

class Application:
    def __init__(self):
        self.data_logger = DataLogger(config.LOG_FILE, config.LOG_LEVEL) # Pass log level
        self.data_logger.log_info("ACR Application Initializing...")

        self.lmm_interface = LMMInterface(data_logger=self.data_logger)

        # InterventionEngine needs logic_engine, app_instance, and data_logger
        # LogicEngine needs data_logger, lmm_interface, and intervention_engine
        # To break circular dependency for init, we can pass intervention_engine to logic_engine later
        self.logic_engine = LogicEngine(
            data_logger=self.data_logger,
            llm_interface=self.lmm_interface,
            intervention_engine=None # Will be set post-IE init
        )
        self.intervention_engine = InterventionEngine(
            logic_engine=self.logic_engine,
            app_instance=self, # Pass self (Application instance)
            data_logger_override=self.data_logger # Explicitly pass logger
        )
        self.logic_engine.intervention_engine = self.intervention_engine # Complete LogicEngine setup

        self.video_sensor = VideoSensor(config.CAMERA_INDEX, self.data_logger)
        self.audio_sensor = self.logic_engine.audio_sensor # Reference from LogicEngine

        self.running = True
        self.sensor_error_active = False # Tracks if any sensor is in a persistent error state

        self.tray_icon = None
        try:
            self.tray_icon = ACRTrayIcon(self)
            if self.logic_engine: # Ensure logic_engine exists before setting callback
                 self.logic_engine.tray_callback = self.update_tray_status_and_notify
        except Exception as e:
            self.data_logger.log_error(f"Failed to initialize system tray: {e}. Application will run without tray icon.", details=str(e))
            self.tray_icon = None


        self._setup_hotkeys()

        initial_mode = self.logic_engine.get_mode()
        self.data_logger.log_info(f"ACR Initialized. Mode: {initial_mode}.")
        if self.intervention_engine: # Check if IE was initialized
            self.intervention_engine.notify_mode_change(initial_mode, f"Application started in {initial_mode} mode.")

        print(f"ACR Initialized. Mode: {initial_mode}. Press Esc to quit.")
        if hasattr(config, 'HOTKEY_CYCLE_MODE') and hasattr(config, 'HOTKEY_PAUSE_RESUME'):
            print(f"Hotkeys: Cycle Mode ({config.HOTKEY_CYCLE_MODE}), Pause/Resume ({config.HOTKEY_PAUSE_RESUME})")
        if hasattr(config, 'HOTKEY_FEEDBACK_HELPFUL') and hasattr(config, 'HOTKEY_FEEDBACK_UNHELPFUL'):
            print(f"Feedback Hotkeys: Helpful ({config.HOTKEY_FEEDBACK_HELPFUL}), Unhelpful ({config.HOTKEY_FEEDBACK_UNHELPFUL})")


    def _setup_hotkeys(self):
        self.data_logger.log_info("Setting up hotkeys...")
        try:
            if hasattr(config, 'HOTKEY_CYCLE_MODE'):
                keyboard.add_hotkey(config.HOTKEY_CYCLE_MODE, lambda: self.on_cycle_mode_pressed(), suppress=True)
            if hasattr(config, 'HOTKEY_PAUSE_RESUME'):
                keyboard.add_hotkey(config.HOTKEY_PAUSE_RESUME, lambda: self.on_pause_resume_pressed(), suppress=True)
            if hasattr(config, 'HOTKEY_FEEDBACK_HELPFUL'):
                keyboard.add_hotkey(config.HOTKEY_FEEDBACK_HELPFUL, lambda: self.on_feedback_helpful_pressed(), suppress=True)
            if hasattr(config, 'HOTKEY_FEEDBACK_UNHELPFUL'):
                keyboard.add_hotkey(config.HOTKEY_FEEDBACK_UNHELPFUL, lambda: self.on_feedback_unhelpful_pressed(), suppress=True)

            keyboard.add_hotkey("esc", self.quit_application_hotkey_wrapper, suppress=True)
            self.data_logger.log_info("Hotkeys registered (or skipped if not in config).")
        except Exception as e:
            log_msg = f"Error setting up hotkeys: {e}. This might require admin/sudo rights or specific OS permissions."
            self.data_logger.log_error(log_msg, details=str(e))
            print(log_msg)

    def on_feedback_helpful_pressed(self):
        self.data_logger.log_info(f"Hotkey '{config.HOTKEY_FEEDBACK_HELPFUL}' pressed.")
        if self.intervention_engine:
            self.intervention_engine.register_feedback("helpful")
        if self.tray_icon:
             self.tray_icon.flash_icon(flash_status=self.logic_engine.get_mode(), duration=0.3, flashes=1)

    def on_feedback_unhelpful_pressed(self):
        self.data_logger.log_info(f"Hotkey '{config.HOTKEY_FEEDBACK_UNHELPFUL}' pressed.")
        if self.intervention_engine:
            self.intervention_engine.register_feedback("unhelpful")
        if self.tray_icon:
             self.tray_icon.flash_icon(flash_status=self.logic_engine.get_mode(), duration=0.3, flashes=1)

    def update_tray_status_and_notify(self, new_mode, old_mode=None):
        # This callback is primarily for the tray icon.
        # TTS notifications for mode changes are handled by on_cycle_mode_pressed and on_pause_resume_pressed
        # by calling intervention_engine.notify_mode_change directly.
        if self.tray_icon:
            effective_display_mode = "error" if self.sensor_error_active and new_mode != "error" else new_mode
            self.tray_icon.update_icon_status(effective_display_mode)

        if old_mode != new_mode: # Log the mode change if it actually changed
            self.data_logger.log_info(f"Mode changed from {old_mode} to {new_mode} (Programmatic: {'Yes' if from_snooze_expiry else 'No'}).")
            # If snooze expired to active, intervention_engine.notify_mode_change is called from logic_engine.get_mode() via set_mode
            # This is a bit convoluted, might simplify later. For now, ensure set_mode in LogicEngine calls IE.notify.
            # Let's ensure notify_mode_change in IE is robust.

    def on_cycle_mode_pressed(self, from_tray=False):
        if self.sensor_error_active and not from_tray: # Allow tray to cycle out of error if sensors recover
            self.data_logger.log_info("Mode cycle via hotkey ignored due to active sensor error.")
            return

        old_mode = self.logic_engine.get_mode()
        self.logic_engine.cycle_mode()
        new_mode = self.logic_engine.get_mode() # This will be the actual new mode after cycle logic

        self.data_logger.log_info(f"Event: Cycle Mode {'from tray' if from_tray else 'Hotkey'}. Mode changed from {old_mode} to {new_mode}")
        if self.intervention_engine:
            self.intervention_engine.notify_mode_change(new_mode) # TTS for the mode change
        if self.tray_icon: # Update tray icon status
            self.tray_icon.update_icon_status("error" if self.sensor_error_active and new_mode != "paused" else new_mode)


    def on_pause_resume_pressed(self, from_tray=False):
        # Allow pausing even if sensor error is active. Resuming might go to error state if still applicable.
        old_mode = self.logic_engine.get_mode()
        self.logic_engine.toggle_pause_resume()
        new_mode = self.logic_engine.get_mode()

        self.data_logger.log_info(f"Event: Pause/Resume {'from tray' if from_tray else 'Hotkey'}. Mode changed from {old_mode} to {new_mode}")
        if self.intervention_engine:
            self.intervention_engine.notify_mode_change(new_mode) # TTS for the mode change
        if self.tray_icon:
            self.tray_icon.update_icon_status("error" if self.sensor_error_active and new_mode != "paused" else new_mode)


    def _check_sensors(self):
        video_err = self.video_sensor.has_error()
        video_err_msg = self.video_sensor.get_last_error() if video_err else ""

        audio_err = False
        audio_err_msg = ""
        if self.audio_sensor: # If audio_sensor was initialized
            audio_err = self.audio_sensor.has_error()
            if audio_err: audio_err_msg = self.audio_sensor.get_last_error()
        elif getattr(config, 'VOSK_MODEL_PATH', None): # If STT was intended but sensor failed to init
            audio_err = True
            audio_err_msg = "AudioSensor (STT) failed to initialize in LogicEngine."

        current_overall_sensor_issue = video_err or audio_err

        if current_overall_sensor_issue and not self.sensor_error_active:
            self.sensor_error_active = True
            self.data_logger.log_error("One or more sensors have entered an error state.")
            if video_err: self.data_logger.log_warning(f"Video sensor error: {video_err_msg}")
            if audio_err: self.data_logger.log_warning(f"Audio sensor error: {audio_err_msg}")

            if self.tray_icon: self.tray_icon.update_icon_status("error")
            if self.intervention_engine: self.intervention_engine.notify_mode_change("error") # TTS for error state

        elif not current_overall_sensor_issue and self.sensor_error_active:
            self.sensor_error_active = False
            self.data_logger.log_info("All sensor errors appear to be resolved.")
            current_mode = self.logic_engine.get_mode()
            if self.tray_icon: self.tray_icon.update_icon_status(current_mode)
            if self.intervention_engine: self.intervention_engine.notify_mode_change(current_mode, "Sensors recovered. Operations resuming.")

        return self.sensor_error_active

    def run(self):
        if self.tray_icon:
            self.tray_icon.run_threaded()

        last_known_mode = self.logic_engine.get_mode() # Initialize with current mode
        loop_counter = 0

        try:
            while self.running:
                loop_counter += 1

                # Check sensors periodically (e.g., every 5 loops = 2.5s if sleep is 0.5s)
                if loop_counter % 5 == 0:
                    self._check_sensors()

                current_mode = self.logic_engine.get_mode() # Checks for snooze expiry

                if current_mode != last_known_mode: # Mode actually changed
                    self.data_logger.log_info(f"Main loop: Detected mode change from {last_known_mode} to {current_mode}")
                    # Tray update is handled by logic_engine.tray_callback or specific hotkey methods.
                    # TTS for mode change is handled by logic_engine.set_mode -> _notify_mode_change -> app.intervention_engine.notify_mode_change
                    last_known_mode = current_mode

                if current_mode == "active" and not self.sensor_error_active:
                    # Video processing (simplified, actual processing would be more complex)
                    frame, video_err_detail = self.video_sensor.get_frame()
                    if video_err_detail:
                        self.data_logger.log_warning(f"Video frame read error in active loop: {video_err_detail}")

                    # Audio processing (STT) is now handled by LogicEngine
                    if self.logic_engine:
                        self.logic_engine.process_audio_input()

                    # Placeholder for LMM processing and proactive interventions based on combined sensor data
                    # This would typically involve passing data to LMMInterface via LogicEngine
                    # and then using InterventionEngine to deliver interventions.

                    # Example of triggering a test intervention (from main branch logic)
                    # This should be driven by LMM or specific logic, not just a counter.
                    # Adopting the new start_intervention structure
                    if loop_counter % getattr(config, 'TEST_INTERVENTION_INTERVAL_SECONDS', 120) == 0 : # Approx every 60s
                        self.data_logger.log_debug("Triggering simulated intervention for feedback testing.")
                        if self.intervention_engine:
                            intervention_details = {
                                "type": "posture_reminder_test",
                                "message": "This is a test of the posture reminder. How's your posture?",
                                "tier": 1, # Example tier
                                "duration": 5 # Short duration for test
                            }
                            self.intervention_engine.start_intervention(intervention_details)

                time.sleep(0.5) # Main loop delay
        except KeyboardInterrupt:
            self.data_logger.log_info("Application run loop interrupted by KeyboardInterrupt.")
        finally:
            self._shutdown()

    def _shutdown(self):
        self.data_logger.log_info("Application shutting down...")
        if hasattr(self, 'video_sensor') and self.video_sensor: self.video_sensor.release()

        if hasattr(self, 'logic_engine') and self.logic_engine:
            self.logic_engine.cleanup()

        if hasattr(self, 'tray_icon') and self.tray_icon: self.tray_icon.stop()

        try:
            keyboard.unhook_all()
            self.data_logger.log_info("Keyboard hotkeys unhooked.")
        except Exception as e:
            self.data_logger.log_warning(f"Could not unhook all keyboard hotkeys: {e}", details=str(e))

        self.data_logger.log_info("Application shutdown complete.")
        print("Application shutdown complete.")

    def quit_application_hotkey_wrapper(self):
        # This wrapper is needed because keyboard.add_hotkey doesn't pass arguments.
        self.quit_application()

    def quit_application(self):
        if not self.running: return
        self.data_logger.log_info("Quit signal received.")
        print("Quit signal received.")
        self.running = False # This will break the main loop in self.run()

if __name__ == "__main__":
    # Set default config values if not present, useful for direct script running or testing
    if not hasattr(config, 'CAMERA_INDEX'): config.CAMERA_INDEX = 0
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "acr_app.log"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"
    if not hasattr(config, 'FEEDBACK_WINDOW_SECONDS'): config.FEEDBACK_WINDOW_SECONDS = 15
    if not hasattr(config, 'MIN_TIME_BETWEEN_INTERVENTIONS'): config.MIN_TIME_BETWEEN_INTERVENTIONS = 300
    if not hasattr(config, 'DEFAULT_INTERVENTION_DURATION'): config.DEFAULT_INTERVENTION_DURATION = 10
    if not hasattr(config, 'SNOOZE_DURATION'): config.SNOOZE_DURATION = 3600
    if not hasattr(config, 'TEST_INTERVENTION_INTERVAL_SECONDS'): config.TEST_INTERVENTION_INTERVAL_SECONDS = 120


    app = None
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt:
        print("Application interrupted by user (Ctrl+C in main).")
        if app and hasattr(app, 'data_logger'): app.data_logger.log_warning("Application interrupted by user (Ctrl+C in main).")
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
        if app and hasattr(app, 'data_logger'):
            app.data_logger.log_error(f"Unhandled exception in main execution: {e}", details=str(e.__traceback__))
        elif not app : # Error during Application init itself
            try: # Attempt to log to a fallback emergency logger
                emergency_logger = DataLogger("emergency_acr_error.log", "ERROR")
                emergency_logger.log_error(f"Critical error during Application init: {e}", details=str(e.__traceback__))
            except: pass # If even emergency logger fails, just print
                print(f"CRITICAL INIT ERROR (logging failed): {e}")
    finally:
        if app and app.running: # If loop was broken by other means than quit_application
            app.quit_application() # Ensure shutdown sequence is called
        print("Main script execution finished.")
