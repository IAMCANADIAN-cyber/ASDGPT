import time
import signal
# import keyboard
import threading
import queue
from typing import Optional, Any
import config
from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine
from core.system_tray import ACRTrayIcon
from core.data_logger import DataLogger
from core.lmm_interface import LMMInterface
from sensors.video_sensor import VideoSensor
from sensors.audio_sensor import AudioSensor

class Application:
    def __init__(self) -> None:
        self.data_logger: DataLogger = DataLogger(config.LOG_FILE)
        self.data_logger.log_info("ACR Application Initializing...")

        # Initialize sensors first, as they might be needed by LogicEngine
        self.video_sensor = VideoSensor(config.CAMERA_INDEX, self.data_logger)
        self.audio_sensor = AudioSensor(self.data_logger)

        # Initialize LMM Interface
        self.lmm_interface = LMMInterface(self.data_logger)

        # Pass sensors and logger to LogicEngine
        self.logic_engine = LogicEngine(
            audio_sensor=self.audio_sensor,
            video_sensor=self.video_sensor,
            logger=self.data_logger,
            lmm_interface=self.lmm_interface
        )
        self.intervention_engine: InterventionEngine = InterventionEngine(self.logic_engine, self)
        self.logic_engine.set_intervention_engine(self.intervention_engine)

        self.running: bool = True
        self.sensor_error_active: bool = False
        self._sensor_lock: threading.Lock = threading.Lock()

        # Queues for sensor data
        self.video_queue: queue.Queue = queue.Queue(maxsize=2) # Max 2 frames to keep it recent
        self.audio_queue: queue.Queue = queue.Queue(maxsize=10) # Allow some buffering for audio chunks

        # Sensor threads
        self.video_thread: Optional[threading.Thread] = None
        self.audio_thread: Optional[threading.Thread] = None

        self.tray_icon: ACRTrayIcon = ACRTrayIcon(self)
        self.logic_engine.tray_callback = self.update_tray_status_and_notify
        self.logic_engine.state_update_callback = self.update_tray_tooltip
        self.logic_engine.notification_callback = self.send_notification

        self._setup_hotkeys()

        self.data_logger.log_info(f"ACR Initialized. Mode: {self.logic_engine.get_mode()}.")
        self.data_logger.log_info(f"Press Esc to quit.")
        self.data_logger.log_info(f"Hotkeys: Cycle Mode ({config.HOTKEY_CYCLE_MODE}), Pause/Resume ({config.HOTKEY_PAUSE_RESUME})")
        self.data_logger.log_info(f"Feedback Hotkeys: Helpful ({config.HOTKEY_FEEDBACK_HELPFUL}), Unhelpful ({config.HOTKEY_FEEDBACK_UNHELPFUL})")


    def _setup_hotkeys(self) -> None:
        self.data_logger.log_info("Setting up hotkeys...")
        try:
            import keyboard
            # Mode control hotkeys
            keyboard.add_hotkey(config.HOTKEY_CYCLE_MODE, lambda: self.on_cycle_mode_pressed(), suppress=True)
            keyboard.add_hotkey(config.HOTKEY_PAUSE_RESUME, lambda: self.on_pause_resume_pressed(), suppress=True)

            # Feedback hotkeys (Task 4.4)
            keyboard.add_hotkey(config.HOTKEY_FEEDBACK_HELPFUL, lambda: self.on_feedback_helpful_pressed(), suppress=True)
            keyboard.add_hotkey(config.HOTKEY_FEEDBACK_UNHELPFUL, lambda: self.on_feedback_unhelpful_pressed(), suppress=True)

            # Quit hotkey
            keyboard.add_hotkey("esc", self.quit_application_hotkey_wrapper, suppress=True)

            self.data_logger.log_info("Hotkeys registered successfully (Mode, Feedback, Quit).")
        except ImportError:
             self.data_logger.log_warning("Keyboard library not found. Hotkeys disabled.")
        except Exception as e:
            log_msg = f"Error setting up hotkeys: {e}. This might require admin/sudo rights."
            self.data_logger.log_error(log_msg)

    # --- Feedback Hotkey Handlers (Task 4.4) ---
    def on_feedback_helpful_pressed(self) -> None:
        self.data_logger.log_info(f"Hotkey '{config.HOTKEY_FEEDBACK_HELPFUL}' pressed.")
        self.intervention_engine.register_feedback("helpful")
        # Optionally, provide some subtle confirmation feedback (e.g., short tray flash or sound)
        if self.tray_icon: # Example: quick flash of current icon
             self.tray_icon.flash_icon(flash_status=self.logic_engine.get_mode(), duration=0.3, flashes=1)


    def on_feedback_unhelpful_pressed(self) -> None:
        self.data_logger.log_info(f"Hotkey '{config.HOTKEY_FEEDBACK_UNHELPFUL}' pressed.")
        self.intervention_engine.register_feedback("unhelpful")
        if self.tray_icon: # Example: quick flash
             self.tray_icon.flash_icon(flash_status=self.logic_engine.get_mode(), duration=0.3, flashes=1)

    def send_notification(self, title: str, message: str) -> None:
        """Sends a notification to the user via the tray icon."""
        if self.tray_icon:
            self.tray_icon.notify_user(title, message)

    # --- Existing Methods (potentially updated) ---
    def update_tray_status_and_notify(self, new_mode: str, old_mode: Optional[str] = None) -> None:
        with self._sensor_lock:
            sensor_error = self.sensor_error_active
        if sensor_error and new_mode != "error":
            if self.tray_icon: self.tray_icon.update_icon_status("error")
        elif self.tray_icon:
            self.tray_icon.update_icon_status(new_mode)

        if old_mode != new_mode:
            log_msg = f"Mode changed from {old_mode} to {new_mode} (Programmatic: {'Yes' if old_mode else 'No'})."
            self.data_logger.log_info(log_msg)
            if new_mode == "active" and old_mode == "snoozed":
                 self.intervention_engine.notify_mode_change(new_mode, "Snooze ended. Co-regulator active.")

    def update_tray_tooltip(self, state_info: dict) -> None:
        if self.tray_icon:
            self.tray_icon.update_tooltip(state_info)

    def on_cycle_mode_pressed(self, from_tray: bool = False) -> None:
        with self._sensor_lock:
            if self.sensor_error_active:
                self.data_logger.log_info("Mode change via hotkey ignored due to active sensor error.")
                return

        old_mode = self.logic_engine.get_mode()
        self.logic_engine.cycle_mode()
        new_mode = self.logic_engine.get_mode()
        log_msg = f"Event: Cycle Mode Hotkey. Mode changed from {old_mode} to {new_mode}"
        self.data_logger.log_info(log_msg)
        self.intervention_engine.notify_mode_change(new_mode)
        if self.tray_icon: self.tray_icon.update_icon_status(new_mode)

    def on_pause_resume_pressed(self, from_tray: bool = False) -> None:
        with self._sensor_lock:
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
        self.intervention_engine.notify_mode_change(new_mode)
        if self.tray_icon:
            with self._sensor_lock:
                sensor_error = self.sensor_error_active
            self.tray_icon.update_icon_status("error" if sensor_error and new_mode != "paused" else new_mode)

    def _check_sensors(self) -> bool:
        with self._sensor_lock:
            video_had_error = self.video_sensor.has_error()
            audio_had_error = self.audio_sensor.has_error()
            current_sensor_issue = video_had_error or audio_had_error

            if current_sensor_issue and not self.sensor_error_active: # New overall sensor error state
                self.data_logger.log_error("One or more sensors have entered an error state.")
                if video_had_error: self.data_logger.log_warning(f"Video sensor error: {self.video_sensor.get_last_error()}")
                if audio_had_error: self.data_logger.log_warning(f"Audio sensor error: {self.audio_sensor.get_last_error()}")

                self.sensor_error_active = True
                if self.tray_icon: self.tray_icon.update_icon_status("error")
                self.intervention_engine.notify_mode_change("error") # Generic sensor error message from IE

            elif not current_sensor_issue and self.sensor_error_active: # Errors just cleared
                self.data_logger.log_info("All sensor errors appear to be resolved.")
                self.sensor_error_active = False
                if self.tray_icon: self.tray_icon.update_icon_status(self.logic_engine.get_mode())
                self.intervention_engine.notify_mode_change(self.logic_engine.get_mode(), "Sensors recovered. Operations resuming.")

            return self.sensor_error_active


    def _video_worker(self) -> None:
        self.data_logger.log_info("Video worker thread started.")
        while self.running:
            with self._sensor_lock:
                sensor_error = self.sensor_error_active
            if self.logic_engine.get_mode() == "active" and not sensor_error:
                try:
                    frame, error = self.video_sensor.get_frame()
                    if error:
                        self.data_logger.log_warning(f"Video sensor error in worker: {error}")
                        # We might still put an error marker or None frame in queue if needed
                        # For now, only put valid frames or rely on _check_sensors
                    if frame is not None:
                        try:
                            self.video_queue.put((frame, error), timeout=0.1) # Short timeout
                        except queue.Full:
                            self.data_logger.log_debug("Video queue full, frame discarded.")
                            pass # Frame discarded
                    elif error: # If frame is None due to error
                         # Potentially put an error marker in the queue if main loop needs to react instantly
                         # For now, _check_sensors will handle persistent errors.
                         pass

                    # Slow down polling if sensor is fine but no frame, or to control CPU.
                    # If get_frame() is truly blocking, this sleep might be less critical
                    # but good for when get_frame() might return quickly with None.
                    time.sleep(0.05) # Poll at ~20 FPS max if sensor is fast

                except Exception as e:
                    self.data_logger.log_error(f"Exception in video worker: {e}")
                    time.sleep(1) # Wait a bit longer after an unexpected error
            else:
                # If not active or sensor error, sleep longer to reduce CPU usage
                time.sleep(0.2)
        self.data_logger.log_info("Video worker thread stopped.")

    def _audio_worker(self) -> None:
        self.data_logger.log_info("Audio worker thread started.")
        while self.running:
            with self._sensor_lock:
                sensor_error = self.sensor_error_active
            if self.logic_engine.get_mode() == "active" and not sensor_error:
                try:
                    chunk, error = self.audio_sensor.get_chunk()
                    if error:
                        self.data_logger.log_warning(f"Audio sensor error in worker: {error}")

                    if chunk is not None:
                        try:
                            self.audio_queue.put((chunk, error), timeout=0.1)
                        except queue.Full:
                            self.data_logger.log_debug("Audio queue full, chunk discarded.")
                            pass # Chunk discarded
                    elif error: # If chunk is None due to error
                        pass

                    # Audio sensor's get_chunk might return None if not enough data is ready,
                    # so a short sleep helps avoid busy-looping.
                    # sounddevice's InputStream usually has its own internal buffering thread.
                    time.sleep(0.05) # Poll frequently but allow other things to run

                except Exception as e:
                    self.data_logger.log_error(f"Exception in audio worker: {e}")
                    time.sleep(1)
            else:
                time.sleep(0.2)
        self.data_logger.log_info("Audio worker thread stopped.")

    def run(self) -> None:
        if self.tray_icon:
            self.tray_icon.run_threaded()

        # Start sensor worker threads
        self.video_thread = threading.Thread(target=self._video_worker, daemon=True)
        self.video_thread.start()
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()

        last_known_mode = self.logic_engine.get_mode()
        loop_counter = 0

        while self.running:
            print(f"Main loop iteration: {loop_counter}")
            loop_counter += 1
            if loop_counter % 10 == 0: # Check sensors slightly less often than main loop spins
                 self._check_sensors()

            current_mode = self.logic_engine.get_mode()

            if current_mode != last_known_mode:
                if self.sensor_error_active:
                    if self.tray_icon: self.tray_icon.update_icon_status("error")
                else:
                    if self.tray_icon: self.tray_icon.update_icon_status(current_mode)
                last_known_mode = current_mode

            video_data_processed = False
            audio_data_processed = False

            if current_mode == "active" and not self.sensor_error_active:
                # Process video queue
                try:
                    frame, video_err = self.video_queue.get_nowait()
                    if video_err:
                        self.data_logger.log_warning(f"Video frame read error from queue: {video_err}")
                    # Process frame if not None (e.g., pass to logic engine)
                    if frame is not None:
                        self.logic_engine.process_video_data(frame)
                        self.data_logger.log_debug(f"Dequeued video frame. Shape: {frame.shape}")
                    video_data_processed = True
                    self.video_queue.task_done() # Signal that item processing is complete
                except queue.Empty:
                    pass # No new video frame

                # Process audio queue
                try:
                    audio_chunk, audio_err = self.audio_queue.get_nowait()
                    if audio_err:
                        self.data_logger.log_warning(f"Audio chunk read error from queue: {audio_err}")
                    if audio_chunk is not None:
                        self.logic_engine.process_audio_data(audio_chunk)
                        self.data_logger.log_debug(f"Dequeued audio chunk. Shape: {audio_chunk.shape}")
                    audio_data_processed = True
                    self.audio_queue.task_done()
                except queue.Empty:
                    pass # No new audio chunk

            # Let the logic engine handle its own periodic updates, including LMM calls
            self.logic_engine.update()

            # Adjust sleep time based on whether we processed sensor data
            if not video_data_processed and not audio_data_processed:
                time.sleep(0.05)
            else:
                time.sleep(0.01)

        self._shutdown()

    def _shutdown(self) -> None:
        self.data_logger.log_info("Application shutting down...")

        # self.running is already False by the time we are here if quit_application() was called
        # The worker threads check self.running, so they should terminate.

        if self.video_thread and self.video_thread.is_alive():
            self.data_logger.log_info("Waiting for video worker thread to join...")
            self.video_thread.join(timeout=2) # Wait for 2 seconds
            if self.video_thread.is_alive():
                 self.data_logger.log_warning("Video worker thread did not join in time.")

        if self.audio_thread and self.audio_thread.is_alive():
            self.data_logger.log_info("Waiting for audio worker thread to join...")
            self.audio_thread.join(timeout=2)
            if self.audio_thread.is_alive():
                 self.data_logger.log_warning("Audio worker thread did not join in time.")

        if hasattr(self, 'video_sensor') and self.video_sensor: self.video_sensor.release()
        if hasattr(self, 'audio_sensor') and self.audio_sensor: self.audio_sensor.release()
        if hasattr(self, 'tray_icon') and self.tray_icon: self.tray_icon.stop()

        try:
            import keyboard
            keyboard.unhook_all()
            self.data_logger.log_info("Keyboard hotkeys unhooked.")
        except ImportError:
            pass
        except Exception as e: # pragma: no cover
            self.data_logger.log_warning(f"Could not unhook all keyboard hotkeys: {e}")

        self.data_logger.log_info("Application shutdown complete.")


    def quit_application_hotkey_wrapper(self) -> None:
        self.quit_application()

    def quit_application(self) -> None:
        if not self.running:
            return
        self.data_logger.log_info("Quit signal received.")
        self.running = False

if __name__ == "__main__":
    if not hasattr(config, 'CAMERA_INDEX'): config.CAMERA_INDEX = 0
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "acr_app.log"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG" # Set to DEBUG for more verbose test output
    if not hasattr(config, 'FEEDBACK_WINDOW_SECONDS'): config.FEEDBACK_WINDOW_SECONDS = 15


    app: Optional[Application] = None
    logger: DataLogger = DataLogger(config.LOG_FILE if hasattr(config, 'LOG_FILE') else "acr_app_emergency.log")

    # Signal handler function
    def signal_handler(signum: int, frame: Optional[Any]) -> None:
        logger.log_warning(f"Signal {signal.Signals(signum).name} received. Initiating shutdown.")
        if app:
            app.quit_application()

    try:
        app = Application()
        logger = app.data_logger

        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        app.run()

    except KeyboardInterrupt: # pragma: no cover
        logger.log_warning("Application interrupted by user (Ctrl+C / SIGINT).")
    except Exception as e: # pragma: no cover
        logger.log_error(f"Unhandled exception in main execution: {e}", details=str(e.__traceback__))
    finally:
        if app and app.running:
            logger.log_info("Ensuring application quit in finally block.")
            app.quit_application()

        logger.log_info("Main script execution finished.")
