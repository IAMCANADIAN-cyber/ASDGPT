import time
import config
from sensors.audio_sensor import AudioSensor
# LMMInterface and InterventionEngine will be passed in __init__

class LogicEngine:
    def __init__(self, data_logger=None, llm_interface=None, intervention_engine=None):
        self.current_mode = config.DEFAULT_MODE
        self.snooze_end_time = 0
        self.previous_mode_before_pause = config.DEFAULT_MODE
        self.tray_callback = None
        self.logger = data_logger
        self.llm_interface = llm_interface
        self.intervention_engine = intervention_engine

        self._log_info(f"LogicEngine initialized. Mode: {self.current_mode}")

        # Initialize AudioSensor with Vosk model path from config
        self.audio_sensor = None
        vosk_model_path = getattr(config, 'VOSK_MODEL_PATH', None)
        if vosk_model_path:
            try:
                self.audio_sensor = AudioSensor(
                    data_logger=self.logger,
                    vosk_model_path=vosk_model_path
                )
                if self.audio_sensor.has_error(): # This includes Vosk init and stream errors
                    self._log_error(f"AudioSensor initialized with error: {self.audio_sensor.get_last_error()}. STT/Audio input might be impaired.")
                    # If error is critical for STT (e.g. Vosk model load failed), STT methods in AudioSensor will reflect this.
            except Exception as e:
                self._log_error(f"Failed to initialize AudioSensor in LogicEngine: {e}", details=str(e))
                self.audio_sensor = None
        else:
            self._log_info("VOSK_MODEL_PATH not configured. STT features will be unavailable.")

    def _log_info(self, message):
        if self.logger: self.logger.log_info(f"LogicEngine: {message}")
        else: print(f"INFO: LogicEngine: {message}")

    def _log_warning(self, message):
        if self.logger: self.logger.log_warning(f"LogicEngine: {message}")
        else: print(f"WARNING: LogicEngine: {message}")

    def _log_error(self, message, details=""):
        if self.logger: self.logger.log_error(f"LogicEngine: {message}", details=details)
        else: print(f"ERROR: LogicEngine: {message} | Details: {details}")

    def _log_debug(self, message):
        if self.logger and hasattr(self.logger, 'log_debug'): self.logger.log_debug(f"LogicEngine: {message}")
        elif self.logger: self.logger.log_info(f"LogicEngine-DEBUG: {message}") # Fallback
        else: print(f"DEBUG: LogicEngine: {message}")

    def get_mode(self):
        initial_mode_for_this_call = self.current_mode
        if self.current_mode == "snoozed":
            if time.time() >= self.snooze_end_time and self.snooze_end_time != 0:
                self._log_info("Snooze expired.")
                self.snooze_end_time = 0
                self.set_mode("active", from_snooze_expiry=True)

        # If mode was changed by snooze expiry, self.current_mode is now updated.
        if initial_mode_for_this_call != self.current_mode:
             self._log_debug(f"Mode changed internally in get_mode (e.g. snooze expiry) from {initial_mode_for_this_call} to {self.current_mode}")
        return self.current_mode

    def set_mode(self, mode, from_snooze_expiry=False):
        if mode not in ["active", "snoozed", "paused", "error"]:
            self._log_warning(f"Attempted to set invalid mode: {mode}")
            return

        old_mode = self.current_mode
        # Allow re-setting active if snooze expired, or if mode is genuinely different
        if mode == old_mode and not (mode == "active" and from_snooze_expiry and old_mode == "snoozed"):
            return

        self._log_info(f"Changing mode from {old_mode} to {mode}")

        if old_mode != "paused" and mode == "paused":
            self.previous_mode_before_pause = old_mode

        self.current_mode = mode

        snooze_duration_config = getattr(config, 'SNOOZE_DURATION', 3600)
        if self.current_mode == "snoozed":
            self.snooze_end_time = time.time() + snooze_duration_config
            self._log_info(f"Snooze activated. Will return to active mode in {snooze_duration_config / 60:.0f} minutes.")
        elif self.current_mode == "active":
            self.snooze_end_time = 0

        self._notify_mode_change(old_mode, new_mode=self.current_mode, from_snooze_expiry=from_snooze_expiry)

    def cycle_mode(self):
        current_actual_mode = self.get_mode() # Ensures snooze expiry is checked
        if current_actual_mode == "active":
            self.set_mode("snoozed")
        elif current_actual_mode == "snoozed":
            self.set_mode("paused")
        elif current_actual_mode == "paused":
            self.set_mode("active")

    def toggle_pause_resume(self):
        current_actual_mode = self.get_mode() # Ensures snooze expiry is checked
        if current_actual_mode == "paused":
            if self.previous_mode_before_pause == "snoozed" and \
               self.snooze_end_time != 0 and time.time() >= self.snooze_end_time:
                self.snooze_end_time = 0
                self.set_mode("active")
            else:
                self.set_mode(self.previous_mode_before_pause)
        else:
            self.set_mode("paused")

    def _notify_mode_change(self, old_mode, new_mode, from_snooze_expiry=False):
        self._log_info(f"Notification: Mode changed from {old_mode} to {new_mode}")
        if self.tray_callback:
            self.tray_callback(new_mode=new_mode, old_mode=old_mode)
        # TTS for mode change is handled by InterventionEngine via Application class

    def process_audio_input(self):
        if not self.audio_sensor or self.audio_sensor.has_error() or not self.audio_sensor.vosk_recognizer:
            # self._log_debug("Audio sensor not available or STT not initialized, skipping audio processing.")
            return

        if self.current_mode != "active":
            # self._log_debug(f"LogicEngine not in 'active' mode (currently {self.current_mode}), skipping audio processing.")
            return

        transcribed_text, error = self.audio_sensor.transcribe_chunk()

        if error and error != "partial":
            self._log_error(f"Error during audio transcription: {error}")
            return

        if error == "partial" and transcribed_text:
            self._log_debug(f"Partial STT result: '{transcribed_text}' - will wait for final.")
            return

        if transcribed_text:
            self._log_info(f"Transcribed text: '{transcribed_text}'")
            if self.llm_interface:
                llm_audio_input = {"type": "speech_transcript", "content": transcribed_text}
                self._log_debug(f"Sending transcribed text to LMM: {llm_audio_input}")
                analysis = self.llm_interface.process_data(audio_data=llm_audio_input)

                if analysis:
                    self._log_debug(f"LMM analysis from audio: {analysis}")
                    if self.intervention_engine:
                        suggestion = self.llm_interface.get_intervention_suggestion(analysis)
                        if suggestion:
                            self._log_info(f"Intervention suggested by LMM based on audio: {suggestion}")
                            # The new InterventionEngine uses start_intervention with a dict
                            intervention_details = {
                                "type": suggestion.get("type", "unknown_suggestion"),
                                "message": suggestion.get("message", "LMM suggested an action."),
                                # Add other relevant parameters from suggestion if any (e.g. duration, tier)
                            }
                            self.intervention_engine.start_intervention(intervention_details)
                        else:
                            self._log_debug("LMM processed audio, but no intervention suggested.")
                else:
                    self._log_debug("LMM processed audio but returned no analysis.")
            else:
                self._log_warning("LMM interface not available to process transcribed text.")

    def cleanup(self):
        self._log_info("LogicEngine cleaning up...")
        if self.audio_sensor:
            self.audio_sensor.release()
            self._log_info("AudioSensor released.")
        self._log_info("LogicEngine cleanup complete.")

if __name__ == '__main__':
    class MockDataLogger:
        def __init__(self): self.log_level = "DEBUG"
        def log_info(self, msg, details=""): print(f"MOCK_LOG_INFO: {msg}")
        def log_warning(self, msg, details=""): print(f"MOCK_LOG_WARN: {msg}")
        def log_error(self, msg, details=""): print(f"MOCK_LOG_ERROR: {msg} | Details: {details}")
        def log_debug(self, msg, details=""): print(f"MOCK_LOG_DEBUG: {msg}")

    class MockLMMInterface:
        def process_data(self, video_data=None, audio_data=None, user_context=None):
            print(f"MOCK_LMM: process_data called with audio_data: {audio_data}")
            if audio_data and audio_data.get("content"):
                if "hello" in audio_data["content"].lower():
                    return {"analysis": "User said hello", "detected_event": "greeting"}
                return {"analysis": f"Processed: {audio_data['content']}"}
            return None
        def get_intervention_suggestion(self, processed_analysis):
            if processed_analysis and processed_analysis.get("detected_event") == "greeting":
                return {"type": "greeting_response", "message": "LMM says: Hello back!"}
            return None

    class MockInterventionEngine:
        def start_intervention(self, details):
            print(f"MOCK_INTERVENTION: start_intervention called with details: {details}")
        def notify_mode_change(self, mode, message=None):
            print(f"MOCK_INTERVENTION: notify_mode_change: mode={mode}, message='{message or ''}'")


    mock_logger = MockDataLogger()
    mock_lmm = MockLMMInterface()
    mock_intervention_engine = MockInterventionEngine()

    # For testing, ensure VOSK_MODEL_PATH is valid or STT part will be skipped.
    # To test STT failure, set config.VOSK_MODEL_PATH to an invalid path before init.
    # Default config.VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"
    print(f"Using VOSK_MODEL_PATH from config: '{getattr(config, 'VOSK_MODEL_PATH', 'Not Set')}' for test.")
    import os
    if not os.path.exists(getattr(config, 'VOSK_MODEL_PATH', '')):
         print(f"WARNING: Vosk model not found at '{getattr(config, 'VOSK_MODEL_PATH', '')}'. STT part of test may not function fully.")

    engine = LogicEngine(data_logger=mock_logger, llm_interface=mock_lmm, intervention_engine=mock_intervention_engine)

    def test_callback(new_mode, old_mode):
        print(f"Test Callback: Mode changed from {old_mode} to {new_mode}")
    engine.tray_callback = test_callback

    print(f"\nInitial mode: {engine.get_mode()}")
    assert engine.get_mode() == "active"

    if engine.audio_sensor and not engine.audio_sensor.has_error() and engine.audio_sensor.vosk_recognizer:
        print("\n--- Testing STT processing. (Mic input needed for real transcription) ---")
        print("Will run process_audio_input() for 5 cycles.")
        engine.set_mode("active")
        for i in range(5):
            print(f"Audio processing cycle {i+1}...")
            engine.process_audio_input() # This will try to get a chunk and transcribe
            time.sleep(0.2) # Simulate some delay
    else:
        print("\n--- STT processing test SKIPPED (AudioSensor init/Vosk model issue or no mic) ---")

    print("\n--- Testing mode switching ---")
    engine.set_mode("active")
    engine.cycle_mode()
    print(f"Mode after cycle 1: {engine.get_mode()}")
    assert engine.get_mode() == "snoozed"

    engine.toggle_pause_resume()
    print(f"Mode after pause: {engine.get_mode()}")
    assert engine.get_mode() == "paused"

    engine.toggle_pause_resume()
    print(f"Mode after resume: {engine.get_mode()}")
    assert engine.get_mode() == "snoozed"

    print("\nSimulating snooze duration passing...")
    engine.snooze_end_time = time.time() - 1
    print(f"Mode after snooze expired (on next get_mode call): {engine.get_mode()}")
    assert engine.current_mode == "active"

    engine.cleanup()
    print("\nLogicEngine tests complete.")
