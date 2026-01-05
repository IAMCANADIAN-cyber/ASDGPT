import time
import config
import datetime
import threading
import json
import os
import subprocess
import platform
from typing import Optional, Any, Dict, List

# Conditional imports for optional dependencies
try:
    import numpy as np
except ImportError:
    np = None

try:
    import scipy.io.wavfile as wavfile
except ImportError:
    wavfile = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import sounddevice as sd
except (ImportError, OSError):
    sd = None

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

        self.last_feedback_eligible_intervention: Dict[str, Any] = {
            "message": None,
            "type": None,
            "timestamp": None
        }
        self.feedback_window: int = config.FEEDBACK_WINDOW_SECONDS if hasattr(config, 'FEEDBACK_WINDOW_SECONDS') else 15

        # Dictionary to track suppressed interventions: {intervention_type: expiry_timestamp}
        self.suppressed_interventions: Dict[str, float] = {}
        self._load_suppressions()

        # Dictionary to track preferred interventions (feedback="helpful"): {intervention_type: {"count": int, "last_helpful": timestamp}}
        self.preferred_interventions: Dict[str, Dict[str, Any]] = {}
        self._load_preferences()

        log_message = "InterventionEngine initialized."
        if self.app and hasattr(self.app, 'data_logger'):
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message + " (DataLogger not available)")

    def _load_suppressions(self) -> None:
        """Loads suppressed interventions from disk."""
        if hasattr(config, 'SUPPRESSIONS_FILE') and os.path.exists(config.SUPPRESSIONS_FILE):
            try:
                with open(config.SUPPRESSIONS_FILE, 'r') as f:
                    self.suppressed_interventions = json.load(f)

                # Clean up expired suppressions on load
                current_time = time.time()
                keys_to_remove = [k for k, v in self.suppressed_interventions.items() if v < current_time]
                for k in keys_to_remove:
                    del self.suppressed_interventions[k]

                if keys_to_remove:
                    self._save_suppressions()

            except Exception as e:
                msg = f"Failed to load suppressions: {e}"
                if self.app and hasattr(self.app, 'data_logger'):
                    self.app.data_logger.log_error(msg)
                else:
                    print(msg)

    def _save_suppressions(self) -> None:
        """Saves suppressed interventions to disk."""
        if hasattr(config, 'SUPPRESSIONS_FILE'):
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(config.SUPPRESSIONS_FILE), exist_ok=True)
                with open(config.SUPPRESSIONS_FILE, 'w') as f:
                    json.dump(self.suppressed_interventions, f)
            except Exception as e:
                msg = f"Failed to save suppressions: {e}"
                if self.app and hasattr(self.app, 'data_logger'):
                    self.app.data_logger.log_error(msg)
                else:
                    print(msg)

    def _load_preferences(self) -> None:
        """Loads preferred interventions from disk."""
        if hasattr(config, 'PREFERENCES_FILE') and os.path.exists(config.PREFERENCES_FILE):
            try:
                with open(config.PREFERENCES_FILE, 'r') as f:
                    self.preferred_interventions = json.load(f)
            except Exception as e:
                msg = f"Failed to load preferences: {e}"
                if self.app and hasattr(self.app, 'data_logger'):
                    self.app.data_logger.log_error(msg)
                else:
                    print(msg)

    def _save_preferences(self) -> None:
        """Saves preferred interventions to disk."""
        if hasattr(config, 'PREFERENCES_FILE'):
            try:
                os.makedirs(os.path.dirname(config.PREFERENCES_FILE), exist_ok=True)
                with open(config.PREFERENCES_FILE, 'w') as f:
                    json.dump(self.preferred_interventions, f)
            except Exception as e:
                msg = f"Failed to save preferences: {e}"
                if self.app and hasattr(self.app, 'data_logger'):
                    self.app.data_logger.log_error(msg)
                else:
                    print(msg)

    def _store_last_intervention(self, message: str, intervention_type_for_logging: str) -> None:
        """Stores details of an intervention that qualifies for feedback."""
        self.last_feedback_eligible_intervention = {
            "message": message,
            "type": intervention_type_for_logging,
            "timestamp": time.time()
        }
        if self.app and self.app.data_logger:
             self.app.data_logger.log_debug(f"Stored intervention for feedback: Type='{intervention_type_for_logging}', Msg='{message}'")

    def _speak(self, text: str, blocking: bool = True) -> None:
        """
        Uses platform-specific TTS commands to speak the text.
        Falls back to logging if the command fails.
        If blocking is True, waits for speech to finish.
        If blocking is False, runs in background.
        """
        log_message = f"SPEAKING: '{text}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)

        def speak_task():
            system = platform.system()
            try:
                if system == "Darwin":  # macOS
                    subprocess.run(["say", text], check=False)
                elif system == "Linux":
                    # Try espeak or spd-say
                    try:
                        subprocess.run(["espeak", text], check=False)
                    except FileNotFoundError:
                        subprocess.run(["spd-say", text], check=False)
                elif system == "Windows":
                    # Use PowerShell for TTS
                    command = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
                    subprocess.run(["powershell", "-Command", command], check=False)
            except Exception as e:
                msg = f"TTS failed: {e}"
                if self.app and self.app.data_logger:
                    self.app.data_logger.log_warning(msg)
                else:
                    print(msg)

        if blocking:
            speak_task()
        else:
            threading.Thread(target=speak_task, daemon=True).start()


    def _play_sound(self, sound_file_path: str) -> None:
        """
        Plays a WAV file using sounddevice.
        This method is blocking (waits for sound to finish).
        """
        log_message = f"PLAYING_SOUND: '{sound_file_path}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)

        if not os.path.exists(sound_file_path):
            msg = f"Sound file not found: {sound_file_path}"
            if self.app and self.app.data_logger:
                self.app.data_logger.log_warning(msg)
            else:
                print(msg)
            return

        if sd is None or wavfile is None:
             msg = "sounddevice or scipy.io.wavfile library not available (or Import failed). Cannot play sound."
             if self.app and self.app.data_logger:
                self.app.data_logger.log_warning(msg)
             else:
                print(msg)
             return

        try:
            samplerate, data = wavfile.read(sound_file_path)
            sd.play(data, samplerate)
            sd.wait() # Block until sound finishes (since this runs in a thread)
        except Exception as e:
            msg = f"Error playing sound '{sound_file_path}': {e}"
            if self.app and self.app.data_logger:
                self.app.data_logger.log_error(msg)
            else:
                print(msg)

    def _show_visual_prompt(self, image_path_or_text: str) -> None:
        """
        Shows a visual prompt.
        If it's an image path, opens it with PIL.
        If it's text, we log it (and in future could open a text window).
        """
        log_message = f"SHOWING_VISUAL: '{image_path_or_text}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)

        if Image is None:
             if self.app and self.app.data_logger:
                self.app.data_logger.log_warning("PIL (Pillow) library not available. Cannot show image.")
             return

        if os.path.exists(image_path_or_text):
            try:
                img = Image.open(image_path_or_text)
                img.show()
            except Exception as e:
                 msg = f"Failed to show image '{image_path_or_text}': {e}"
                 if self.app and self.app.data_logger:
                    self.app.data_logger.log_error(msg)
                 else:
                    print(msg)
        else:
             # Just text? For now, we only log text prompts as we don't have a GUI window manager here.
             pass

    def _capture_image(self, details: str) -> None:
        # Placeholder for capturing an image
        log_message = f"CAPTURING_IMAGE: '{details}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)
        # In a real implementation, this would trigger the video sensor to save a snapshot

    def _record_video(self, details: str) -> None:
        # Placeholder for recording video
        log_message = f"RECORDING_VIDEO: '{details}'"
        if self.app and self.app.data_logger:
            self.app.data_logger.log_info(log_message)
        else:
            print(log_message)

    def _wait(self, duration: float) -> None:
        """Waits for a specified duration, respecting the stop signal."""
        start = time.time()
        while time.time() - start < duration:
            if not self._intervention_active.is_set():
                break
            time.sleep(0.1)

    def _run_sequence(self, sequence: List[Dict[str, Any]], logger: Any) -> None:
        """Executes a sequence of actions."""
        for step in sequence:
            if not self._intervention_active.is_set():
                break

            action = step.get("action")

            if action == "speak":
                content = step.get("content", "")
                # Blocking speech in a sequence to maintain timing
                self._speak(content, blocking=True)

            elif action == "sound":
                file_path = step.get("file", "")
                self._play_sound(file_path)

            elif action == "visual_prompt":
                content = step.get("content", "")
                self._show_visual_prompt(content)

            elif action == "capture_image":
                content = step.get("content", "")
                self._capture_image(content)

            elif action == "record_video":
                content = step.get("content", "")
                self._record_video(content)

            elif action == "wait":
                duration = step.get("duration", 0)
                self._wait(duration)

            else:
                if logger:
                    logger.log_warning(f"Unknown action in sequence: {action}")

    def _run_intervention_thread(self) -> None:
        """The actual intervention logic run in a separate thread."""
        intervention_type = self._current_intervention_details.get("type", "unknown_intervention")
        message = self._current_intervention_details.get("message", "No message provided.")
        # If a card was found, use its sequence. Otherwise, fallback to single message.
        sequence = self._current_intervention_details.get("sequence")

        # Backward compatibility for 'tier' if needed, though 'sequence' is preferred
        tier = self._current_intervention_details.get("tier", 1)

        log_prefix = f"Intervention (Type: {intervention_type})"
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None

        def log_info(msg: str) -> None:
            if logger:
                logger.log_info(msg)
            else:
                print(msg)

        def log_debug(msg: str) -> None:
            if logger:
                logger.log_debug(msg)
            else:
                print(msg)

        log_info(f"{log_prefix}: Started.")

        # Flash tray icon if applicable
        current_app_mode = self.logic_engine.get_mode()
        if self.app and hasattr(self.app, 'tray_icon') and self.app.tray_icon:
             if intervention_type not in ["mode_change_notification"]:
                log_debug(f"{log_prefix}: Flashing tray icon.")
                flash_icon_type = "error" if "error" in intervention_type else "active"
                self.app.tray_icon.flash_icon(flash_status=flash_icon_type, original_status=current_app_mode)


        if sequence:
            # Execute the defined sequence from the library card
            self._run_sequence(sequence, logger)
        else:
            # Fallback: Just speak the message (Legacy/Simple mode)
            # Default to blocking for backward compatibility in single-message mode,
            # as this thread is dedicated to the intervention anyway.
            self._speak(message, blocking=True)

            # Store simple interventions for feedback
            if intervention_type not in ["mode_change_notification", "error_notification_spoken"]:
                self._store_last_intervention(message, intervention_type)

        # For library interventions, we store feedback *after* execution if needed.
        # But 'message' might not be a single string in a sequence.
        # So we use the 'description' or the primary message if available.
        if sequence and intervention_type not in ["mode_change_notification"]:
             description = self._current_intervention_details.get("description", intervention_type)
             self._store_last_intervention(description, intervention_type)


        if not self._intervention_active.is_set():
            log_info(f"{log_prefix}: Stopped early by request.")
        else:
            log_info(f"{log_prefix}: Completed.")

        self._intervention_active.clear()
        self._current_intervention_details = {}

    def suppress_intervention(self, intervention_type: str, duration_minutes: int) -> None:
        """Suppress a specific intervention type for a duration."""
        expiry_time = time.time() + (duration_minutes * 60)
        self.suppressed_interventions[intervention_type] = expiry_time
        self._save_suppressions()

        msg = f"Intervention type '{intervention_type}' suppressed for {duration_minutes} minutes."
        if self.app and hasattr(self.app, 'data_logger'):
            self.app.data_logger.log_info(msg)
        else:
            print(msg)

    def get_suppressed_intervention_types(self) -> List[str]:
        """Returns a list of currently suppressed intervention types/IDs."""
        current_time = time.time()
        # Clean up first (in memory, save will happen on next modification or load)
        active_suppressions = []
        keys_to_remove = []
        for k, v in self.suppressed_interventions.items():
            if v > current_time:
                active_suppressions.append(k)
            else:
                keys_to_remove.append(k)

        # Optional: Clean up expired ones from dict now to keep it fresh
        if keys_to_remove:
            for k in keys_to_remove:
                del self.suppressed_interventions[k]
            self._save_suppressions()

        return active_suppressions

    def get_preferred_intervention_types(self) -> List[str]:
        """Returns a list of preferred intervention types/IDs (sorted by most helpful first)."""
        # Sort by count descending
        sorted_prefs = sorted(self.preferred_interventions.items(), key=lambda item: item[1].get("count", 0), reverse=True)
        # Return just the keys
        return [k for k, v in sorted_prefs]

    def start_intervention(self, intervention_details: Dict[str, Any]) -> bool:
        """
        Starts an intervention.
        intervention_details can contain:
        - 'id': ID of a card in InterventionLibrary (preferred).
        - 'type' & 'message': Fallback for ad-hoc interventions.
        """
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None

        intervention_id = intervention_details.get("id")
        card = None

        # 1. Try to fetch from library if ID is present
        if intervention_id:
            card = self.library.get_intervention_by_id(intervention_id)

        # 2. If no ID or card not found, check if LMM suggested a type that matches a category/card
        # (This is a future enhancement, for now we stick to explicit ID or ad-hoc)

        intervention_type = intervention_details.get("type")
        custom_message = intervention_details.get("message")

        # Prepare execution details
        execution_details = {}

        if card:
            execution_details = card.copy()
            execution_details["type"] = card["id"] # Use ID as type for logging
            # If caller provided specific message override, we *could* use it,
            # but usually cards have their own sequences.
        elif intervention_type and custom_message:
            # Ad-hoc intervention (legacy support or dynamic LMM message)
            execution_details = {
                "type": intervention_type,
                "message": custom_message,
                "tier": intervention_details.get("tier", 1)
            }
        else:
            if logger:
                logger.log_warning("Intervention attempt failed: valid 'id' or ('type' + 'message') required.")
            else:
                print("Intervention attempt failed: valid 'id' or ('type' + 'message') required.")
            return False

        # Check for suppression
        # IMPORTANT: Use the resolved ID/type from execution_details if available (e.g. card['id'])
        check_type = execution_details.get("type", intervention_type)

        if check_type in self.suppressed_interventions:
            expiry = self.suppressed_interventions[check_type]
            if time.time() < expiry:
                remaining_mins = int((expiry - time.time()) / 60)
                if logger:
                    logger.log_info(f"Intervention '{check_type}' skipped (suppressed for {remaining_mins} more mins).")
                else:
                    print(f"Intervention '{check_type}' skipped (suppressed for {remaining_mins} more mins).")
                return False
            else:
                # Expired, remove from list
                del self.suppressed_interventions[check_type]

        # Critical: If called from within an existing sequence or thread, this check might fail.
        # But generally start_intervention is called from LogicEngine main thread.
        # If an intervention is active, we generally want to ignore new ones unless we have a priority system (TODO).
        if self._intervention_active.is_set():
            # FUTURE: If new intervention has higher priority (Tier 3 vs 1), stop current and start new.
            if logger:
                logger.log_info(f"Intervention attempt ignored: An intervention is already active.")
            else:
                print(f"Intervention attempt ignored: An intervention is already active.")
            return False

        current_app_mode = self.logic_engine.get_mode()
        if current_app_mode != "active":
            if logger:
                logger.log_info(f"Intervention suppressed: Mode is {current_app_mode}")
            else:
                print(f"Intervention suppressed: Mode is {current_app_mode}")
            return False

        current_time = time.time()
        # Rate limiting (skip for mode changes or errors)
        is_system_msg = execution_details["type"] in ["mode_change_notification", "error_notification", "error_notification_spoken"]
        if not is_system_msg and \
           (current_time - self.last_intervention_time < config.MIN_TIME_BETWEEN_INTERVENTIONS):
            if logger:
                logger.log_info(f"Intervention '{execution_details['type']}' suppressed: Too soon since last intervention.")
            else:
                print(f"Intervention '{execution_details['type']}' suppressed: Too soon since last intervention.")
            return False

        self._intervention_active.set()
        self._current_intervention_details = execution_details
        self.last_intervention_time = current_time

        self.intervention_thread = threading.Thread(target=self._run_intervention_thread)
        self.intervention_thread.daemon = True
        self.intervention_thread.start()

        msg_str = f"Intervention '{execution_details['type']}'"
        if "tier" in execution_details:
             msg_str += f" (Tier {execution_details['tier']})"
        msg_str += " initiated."

        if logger:
            logger.log_info(msg_str)
            logger.log_event("intervention_start", execution_details)
        else:
            print(msg_str)
        return True

    def stop_intervention(self) -> None:
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None
        if self._intervention_active.is_set():
            if logger:
                logger.log_info(f"Stopping intervention...")
            else:
                print(f"Stopping intervention...")
            self._intervention_active.clear()
        else:
            if logger:
                logger.log_info("No active intervention to stop.")
            else:
                print("No active intervention to stop.")

    def shutdown(self) -> None:
        """Gracefully shuts down the InterventionEngine."""
        logger = self.app.data_logger if self.app and hasattr(self.app, 'data_logger') else None
        if logger:
            logger.log_info("InterventionEngine shutting down...")
        else:
            print("InterventionEngine shutting down...")

        self.stop_intervention()
        if self.intervention_thread and self.intervention_thread.is_alive():
            if logger:
                logger.log_info("Waiting for intervention thread to finish...")
            self.intervention_thread.join(timeout=3.0)
            if self.intervention_thread.is_alive():
                if logger:
                    logger.log_warning("Intervention thread did not finish in time.")

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
            # Mode changes happen on main thread (typically), so we speak non-blocking
            self._speak(message, blocking=False)

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

        log_msg_console = f"Feedback '{feedback_value}' logged for intervention: '{self.last_feedback_eligible_intervention['message']}'"
        if logger:
            logger.log_event(event_type="user_feedback", payload=feedback_payload)
            logger.log_info(log_msg_console)
        else:
            print(f"DataLogger not available. Feedback event: {feedback_payload}")

        # Apply suppression if feedback is unhelpful
        if feedback_value.lower() == "unhelpful":
            suppression_time = config.FEEDBACK_SUPPRESSION_MINUTES if hasattr(config, 'FEEDBACK_SUPPRESSION_MINUTES') else 240
            self.suppress_intervention(self.last_feedback_eligible_intervention["type"], suppression_time)
        elif feedback_value.lower() == "helpful":
            # Track preference
            itype = self.last_feedback_eligible_intervention["type"]
            if itype:
                if itype not in self.preferred_interventions:
                    self.preferred_interventions[itype] = {"count": 0, "last_helpful": 0}

                self.preferred_interventions[itype]["count"] += 1
                self.preferred_interventions[itype]["last_helpful"] = time.time()
                self._save_preferences()

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

    print("\n--- Test 1: Simple Ad-Hoc Intervention (Legacy) ---")
    details_t1 = {"type": "posture_check", "message": "Sit straight!"}
    intervention_engine.start_intervention(details_t1)
    time.sleep(0.2)

    print("\n--- Test 2: Library Intervention (Sequence) ---")
    # Using 'box_breathing' from library (assuming it's there)
    # We cheat the timer for test
    intervention_engine.last_intervention_time = 0
    details_t2 = {"id": "box_breathing"}
    intervention_engine.start_intervention(details_t2)
    time.sleep(1) # Let it run a bit
    intervention_engine.stop_intervention()
    time.sleep(0.2)

    print("\n--- Test 3: Stop early ---")
    intervention_engine.last_intervention_time = 0
    details_t3 = {"id": "visual_scan"}
    intervention_engine.start_intervention(details_t3)
    time.sleep(0.1)
    intervention_engine.stop_intervention()
    time.sleep(0.1)

    print("\n--- Test 4: Start Intervention with missing data ---")
    intervention_engine.start_intervention({"just_random": "data"})
    time.sleep(0.1)

    print("\n--- Test 5: Suppressed by Mode ---")
    mock_logic_engine.set_mode("paused")
    intervention_engine.start_intervention(details_t1)
    mock_logic_engine.set_mode("active")
    time.sleep(0.1)

    print("\n--- Test 6: Capture Image Action ---")
    intervention_engine.last_intervention_time = 0
    details_t6 = {"id": "sultry_persona_prompt"}
    intervention_engine.start_intervention(details_t6)
    time.sleep(0.2)
    intervention_engine.stop_intervention()

    print("\nInterventionEngine tests complete.")
