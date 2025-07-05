import time
import keyboard # Ensure this is installed
import config
from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine
from core.system_tray import ACRTrayIcon
from core.data_logger import DataLogger
from sensors.video_sensor import VideoSensor
from sensors.audio_sensor import AudioSensor

class Application:
    def __init__(self):
        self.data_logger = DataLogger(config.LOG_FILE)
        self.data_logger.log_info("ACR Application Initializing...")

        # Initialize LMMInterface first if LogicEngine depends on it
        # For now, assuming LMMInterface can be initialized standalone or LogicEngine handles its absence
        self.lmm_interface = None # Placeholder, will be initialized if needed by LogicEngine
        # from core.lmm_interface import LMMInterface # Import if not already
        # self.lmm_interface = LMMInterface(data_logger=self.data_logger)


        # LogicEngine now takes data_logger, lmm_interface, and intervention_engine
        self.logic_engine = LogicEngine(
            data_logger=self.data_logger,
            llm_interface=self.lmm_interface,
            # intervention_engine will be passed after it's created to avoid circular dependency if any
        )
        self.intervention_engine = InterventionEngine(self.logic_engine, self, self.data_logger)
        self.logic_engine.intervention_engine = self.intervention_engine # Now pass it to logic_engine

        # VideoSensor is straightforward
        self.video_sensor = VideoSensor(config.CAMERA_INDEX, self.data_logger)

        # AudioSensor is now initialized within LogicEngine if STT is used.
        # We can keep a reference here if direct access is needed for other purposes,
        # or rely on logic_engine.audio_sensor.
        # For now, let's assume LogicEngine manages its AudioSensor instance primarily.
        self.audio_sensor = self.logic_engine.audio_sensor
        # This makes self.audio_sensor in Application point to the same instance as in LogicEngine,
        # or None if LogicEngine failed to initialize it.

        self.running = True
        self.sensor_error_active = False

        self.tray_icon = ACRTrayIcon(self)
        self.logic_engine.tray_callback = self.update_tray_status_and_notify

        self._setup_hotkeys()

        self.data_logger.log_info(f"ACR Initialized. Mode: {self.logic_engine.get_mode()}.")
        # self.intervention_engine.notify_mode_change(self.logic_engine.get_mode(), f"Application started in {self.logic_engine.get_mode()} mode.")

        print(f"ACR Initialized. Mode: {self.logic_engine.get_mode()}. Press Esc to quit.")
        print(f"Hotkeys: Cycle Mode ({config.HOTKEY_CYCLE_MODE}), Pause/Resume ({config.HOTKEY_PAUSE_RESUME})")
        print(f"Feedback Hotkeys: Helpful ({config.HOTKEY_FEEDBACK_HELPFUL}), Unhelpful ({config.HOTKEY_FEEDBACK_UNHELPFUL})")


    def _setup_hotkeys(self):
        self.data_logger.log_info("Setting up hotkeys...")
        try:
            # Mode control hotkeys
            keyboard.add_hotkey(config.HOTKEY_CYCLE_MODE, lambda: self.on_cycle_mode_pressed(), suppress=True)
            keyboard.add_hotkey(config.HOTKEY_PAUSE_RESUME, lambda: self.on_pause_resume_pressed(), suppress=True)

            # Feedback hotkeys (Task 4.4)
            keyboard.add_hotkey(config.HOTKEY_FEEDBACK_HELPFUL, lambda: self.on_feedback_helpful_pressed(), suppress=True)
            keyboard.add_hotkey(config.HOTKEY_FEEDBACK_UNHELPFUL, lambda: self.on_feedback_unhelpful_pressed(), suppress=True)

            # Quit hotkey
            keyboard.add_hotkey("esc", self.quit_application_hotkey_wrapper, suppress=True)

            self.data_logger.log_info("Hotkeys registered successfully (Mode, Feedback, Quit).")
        except Exception as e:
            log_msg = f"Error setting up hotkeys: {e}. This might require admin/sudo rights."
            self.data_logger.log_error(log_msg)
            print(log_msg)

    # --- Feedback Hotkey Handlers (Task 4.4) ---
    def on_feedback_helpful_pressed(self):
        self.data_logger.log_info(f"Hotkey '{config.HOTKEY_FEEDBACK_HELPFUL}' pressed.")
        self.intervention_engine.register_feedback("helpful")
        # Optionally, provide some subtle confirmation feedback (e.g., short tray flash or sound)
        if self.tray_icon: # Example: quick flash of current icon
             self.tray_icon.flash_icon(flash_status=self.logic_engine.get_mode(), duration=0.3, flashes=1)


    def on_feedback_unhelpful_pressed(self):
        self.data_logger.log_info(f"Hotkey '{config.HOTKEY_FEEDBACK_UNHELPFUL}' pressed.")
        self.intervention_engine.register_feedback("unhelpful")
        if self.tray_icon: # Example: quick flash
             self.tray_icon.flash_icon(flash_status=self.logic_engine.get_mode(), duration=0.3, flashes=1)

    # --- Existing Methods (potentially updated) ---
    def update_tray_status_and_notify(self, new_mode, old_mode=None):
        if self.sensor_error_active and new_mode != "error":
            if self.tray_icon: self.tray_icon.update_icon_status("error")
        elif self.tray_icon:
            self.tray_icon.update_icon_status(new_mode)

        if old_mode != new_mode:
            log_msg = f"Mode changed from {old_mode} to {new_mode} (Programmatic: {'Yes' if old_mode else 'No'})."
            self.data_logger.log_info(log_msg)
            # print(log_msg) # Already printed by LogicEngine usually
            if new_mode == "active" and old_mode == "snoozed":
                 self.intervention_engine.notify_mode_change(new_mode, "Snooze ended. Co-regulator active.")

    def on_cycle_mode_pressed(self, from_tray=False):
        if self.sensor_error_active:
            self.data_logger.log_info("Mode change via hotkey ignored due to active sensor error.")
            return

        old_mode = self.logic_engine.get_mode()
        self.logic_engine.cycle_mode()
        new_mode = self.logic_engine.get_mode()
        log_msg = f"Event: Cycle Mode Hotkey. Mode changed from {old_mode} to {new_mode}"
        self.data_logger.log_info(log_msg)
        # print(log_msg) # InterventionEngine will print its SPEAKING line
        self.intervention_engine.notify_mode_change(new_mode)
        if self.tray_icon: self.tray_icon.update_icon_status(new_mode)

    def on_pause_resume_pressed(self, from_tray=False):
        if self.sensor_error_active and self.logic_engine.get_mode() == "paused":
            pass
        elif self.sensor_error_active:
            self.data_logger.log_info("Pause/Resume via hotkey modified due to active sensor error.")
            pass

        old_mode = self.logic_engine.get_mode()
        self.logic_engine.toggle_pause_resume()
        new_mode = self.logic_engine.get_mode()
        log_msg = f"Event: Pause/Resume Hotkey. Mode changed from {old_mode} to {new_mode}"
        self.data_logger.log_info(log_msg)
        # print(log_msg)
        self.intervention_engine.notify_mode_change(new_mode)
        if self.tray_icon:
            self.tray_icon.update_icon_status("error" if self.sensor_error_active and new_mode != "paused" else new_mode)

    def _check_sensors(self):
        video_had_error = self.video_sensor.has_error()
        # Check audio sensor via logic_engine if it's managed there, or directly if self.audio_sensor is always populated
        audio_had_error = False
        audio_error_msg = ""
        if self.logic_engine.audio_sensor: # Check if audio_sensor was successfully initialized
            audio_had_error = self.logic_engine.audio_sensor.has_error()
            if audio_had_error:
                audio_error_msg = self.logic_engine.audio_sensor.get_last_error()
        elif config.VOSK_MODEL_PATH: # If VOSK_MODEL_PATH was set, implies STT was intended
            # This case means audio_sensor failed to init in LogicEngine
            audio_had_error = True
            audio_error_msg = "AudioSensor (STT) failed to initialize in LogicEngine."
            # Log this specific failure if not already logged sufficiently by LogicEngine
            # self.data_logger.log_warning(audio_error_msg) # LogicEngine likely logged this already

        current_sensor_issue = video_had_error or audio_had_error

        if current_sensor_issue and not self.sensor_error_active: # New overall sensor error state
            self.data_logger.log_error("One or more sensors have entered an error state.")
            if video_had_error: self.data_logger.log_warning(f"Video sensor error: {self.video_sensor.get_last_error()}")
            if audio_had_error: self.data_logger.log_warning(f"Audio sensor error: {audio_error_msg}")

            self.sensor_error_active = True
            if self.tray_icon: self.tray_icon.update_icon_status("error")
            self.intervention_engine.notify_mode_change("error") # Generic sensor error message from IE

        elif not current_sensor_issue and self.sensor_error_active: # Errors just cleared
            self.data_logger.log_info("All sensor errors appear to be resolved.")
            self.sensor_error_active = False
            if self.tray_icon: self.tray_icon.update_icon_status(self.logic_engine.get_mode())
            self.intervention_engine.notify_mode_change(self.logic_engine.get_mode(), "Sensors recovered. Operations resuming.")

        return self.sensor_error_active


    def run(self):
        if self.tray_icon:
            self.tray_icon.run_threaded()

        last_known_mode = self.logic_engine.get_mode()
        loop_counter = 0

        while self.running:
            loop_counter += 1
            if loop_counter % 5 == 0:
                 self._check_sensors()

            current_mode = self.logic_engine.get_mode()

            if current_mode != last_known_mode:
                if self.sensor_error_active:
                    if self.tray_icon: self.tray_icon.update_icon_status("error")
                else:
                    if self.tray_icon: self.tray_icon.update_icon_status(current_mode)
                last_known_mode = current_mode

            if current_mode == "active" and not self.sensor_error_active:
                # Video processing
                frame, video_err = self.video_sensor.get_frame()
                if video_err:
                    self.data_logger.log_warning(f"Video frame read error in active loop: {video_err}")

                # Audio processing (including STT) is now handled by LogicEngine
                self.logic_engine.process_audio_input()

                # Example of LMM processing based on video (if needed directly here, or move to LogicEngine)
                # if frame is not None and self.logic_engine.lmm_interface:
                #     video_analysis = self.logic_engine.lmm_interface.process_data(video_data={"frame_summary": "new_frame"})
                #     if video_analysis:
                #         video_suggestion = self.logic_engine.lmm_interface.get_intervention_suggestion(video_analysis)
                #         if video_suggestion:
                #             self.intervention_engine.provide_intervention(
                #                 video_suggestion["type"], video_suggestion.get("message")
                #             )

                # --- Example of triggering a test intervention for feedback ---
                # This should ideally be driven by LMM or specific logic, not just a counter.
                # Keeping it for now for testing feedback mechanism.
                if loop_counter % 60 == 0 : # Approx every 30s (if sleep is 0.5s)
                    self.data_logger.log_debug("Triggering simulated intervention for feedback testing.")
                    self.intervention_engine.provide_intervention(
                        intervention_type="posture_reminder", # Specific type
                        custom_message="How's your posture right now? Take a moment to adjust if needed."
                    )
                # --- End of example ---

            time.sleep(0.5)
        self._shutdown()

    def _shutdown(self):
        self.data_logger.log_info("Application shutting down...")
        if hasattr(self, 'video_sensor') and self.video_sensor: self.video_sensor.release()

        # Audio sensor is managed by LogicEngine, so call its cleanup
        if hasattr(self, 'logic_engine') and self.logic_engine:
            self.logic_engine.cleanup() # This will release the audio_sensor

        if hasattr(self, 'tray_icon') and self.tray_icon: self.tray_icon.stop()

        try:
            keyboard.unhook_all()
            self.data_logger.log_info("Keyboard hotkeys unhooked.")
        except Exception as e: # pragma: no cover
            self.data_logger.log_warning(f"Could not unhook all keyboard hotkeys: {e}")

        self.data_logger.log_info("Application shutdown complete.")
        print("Application shutdown complete.")


    def quit_application_hotkey_wrapper(self):
        self.quit_application()

    def quit_application(self):
        if not self.running:
            return
        self.data_logger.log_info("Quit signal received.")
        print("Quit signal received.")
        self.running = False

if __name__ == "__main__":
    if not hasattr(config, 'CAMERA_INDEX'): config.CAMERA_INDEX = 0
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "acr_app.log"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG" # Set to DEBUG for more verbose test output
    if not hasattr(config, 'FEEDBACK_WINDOW_SECONDS'): config.FEEDBACK_WINDOW_SECONDS = 15


    app = None
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt: # pragma: no cover
        print("Application interrupted by user (Ctrl+C).")
        if app and hasattr(app, 'data_logger'): app.data_logger.log_warning("Application interrupted by user (Ctrl+C).")
    except Exception as e: # pragma: no cover
        print(f"An unexpected error occurred in main: {e}")
        if app and hasattr(app, 'data_logger'):
            app.data_logger.log_error(f"Unhandled exception in main execution: {e}", details=str(e.__traceback__))
        elif not app :
            try:
                temp_logger = DataLogger("emergency_error.log")
                temp_logger.log_error(f"Critical error during Application init: {e}", details=str(e.__traceback__))
            except: pass
    finally:
        if app and app.running:
            app.quit_application()
        print("Main script execution finished.")
