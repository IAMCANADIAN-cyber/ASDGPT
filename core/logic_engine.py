import time
import config
from sensors.audio_sensor import AudioSensor # Import AudioSensor
from core.lmm_interface import LMMInterface # Assuming LMMInterface is needed for processing

class LogicEngine:
    def __init__(self, data_logger=None, llm_interface=None, intervention_engine=None): # Added engines
        self.current_mode = config.DEFAULT_MODE
        self.snooze_end_time = 0
        self.previous_mode_before_pause = config.DEFAULT_MODE
        self.tray_callback = None
        self.logger = data_logger
        self.llm_interface = llm_interface
        self.intervention_engine = intervention_engine # Store intervention engine

        self._log_info(f"LogicEngine initialized. Mode: {self.current_mode}")

        # Initialize AudioSensor with Vosk model path from config
        self.audio_sensor = None
        try:
            self.audio_sensor = AudioSensor(
                data_logger=self.logger,
                vosk_model_path=config.VOSK_MODEL_PATH
            )
            if self.audio_sensor.has_error() and "Vosk init failed" in self.audio_sensor.get_last_error():
                self._log_error(f"AudioSensor STT initialization failed: {self.audio_sensor.get_last_error()}. Voice input will be disabled.")
                self.audio_sensor = None # Disable if STT failed critically
            elif self.audio_sensor.has_error():
                 self._log_warning(f"AudioSensor initialized with non-critical error: {self.audio_sensor.get_last_error()}")

        except Exception as e:
            self._log_error(f"Failed to initialize AudioSensor in LogicEngine: {e}", details=str(e))
            self.audio_sensor = None

    def _log_info(self, message):
        if self.logger: self.logger.log_info(f"LogicEngine: {message}")
        else: print(f"INFO: LogicEngine: {message}")

    def _log_warning(self, message):
        if self.logger: self.logger.log_warning(f"LogicEngine: {message}")
        else: print(f"WARNING: LogicEngine: {message}")

    def _log_error(self, message, details=""):
        if self.logger: self.logger.log_error(f"LogicEngine: {message}", details)
        else: print(f"ERROR: LogicEngine: {message} | Details: {details}")

    def get_mode(self):
        # old_mode = self.current_mode # This variable is not used before being reassigned
        # The original logic for old_mode here seemed to be for checking if mode changed *within* this call
        # due to snooze expiry. Let's preserve the intent.
        initial_mode_for_this_call = self.current_mode
        if self.current_mode == "snoozed":
            if time.time() >= self.snooze_end_time and self.snooze_end_time != 0:
                print("Snooze expired.")
                self.snooze_end_time = 0 # Reset snooze time
                self.set_mode("active", from_snooze_expiry=True)
                # set_mode will call _notify_mode_change

        # If mode was changed by snooze expiry, self.current_mode is now updated.
        # If not, it's the same as old_mode.
        return self.current_mode

    def set_mode(self, mode, from_snooze_expiry=False):
        if mode not in ["active", "snoozed", "paused", "error"]: # Added error mode
            print(f"Warning: Attempted to set invalid mode: {mode}")
            return

        old_mode = self.current_mode
        if mode == old_mode and not from_snooze_expiry : # Allow re-setting active if snooze expired
            # (e.g. if already active, but snooze expired, we still want notification)
            # This condition might need refinement based on desired notification behavior
            if not (mode == "active" and from_snooze_expiry and old_mode == "snoozed"):
                 return


        print(f"LogicEngine: Changing mode from {old_mode} to {mode}")

        if old_mode != "paused" and mode == "paused":
            self.previous_mode_before_pause = old_mode

        self.current_mode = mode

        if self.current_mode == "snoozed":
            self.snooze_end_time = time.time() + config.SNOOZE_DURATION
            print(f"Snooze activated. Will return to active mode in {config.SNOOZE_DURATION / 60:.0f} minutes.")
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
        print(f"LogicEngine Notification: Mode changed from {old_mode} to {new_mode}")
        if self.tray_callback:
            # Pass both old and new mode for more context if needed by callback
            self.tray_callback(new_mode=new_mode, old_mode=old_mode)

    def process_audio_input(self):
        """
        Called periodically to process audio input, transcribe it,
        and potentially send it to the LMM.
        """
        if not self.audio_sensor:
            # self._log_info("Audio sensor not available, skipping audio processing.")
            return

        if self.current_mode != "active": # Only process audio if active
            # self._log_info(f"LogicEngine not in 'active' mode (currently {self.current_mode}), skipping audio processing.")
            return

        # Attempt to get transcribed text
        # Using transcribe_chunk for potentially faster partial results,
        # or get_final_transcription if longer utterances are expected.
        # For now, let's try to get any new text from the current chunk.

        # The audio_sensor's transcribe_chunk now handles getting a new audio chunk if none is provided.
        transcribed_text, error = self.audio_sensor.transcribe_chunk()

        if error and error != "partial":
            self._log_error(f"Error during audio transcription: {error}")
            return

        if error == "partial" and transcribed_text:
            self._log_info(f"Partial STT result: '{transcribed_text}' - buffering or waiting for final.")
            # We might want to buffer partial results or handle them differently.
            # For now, we'll only send non-partial (i.e., more complete) results to LMM.
            return # Don't send partial results to LMM yet

        if transcribed_text:
            self._log_info(f"Transcribed text: '{transcribed_text}'")
            if self.llm_interface:
                # We need to define how transcribed audio fits into process_data
                # For now, let's pass it as 'audio_data' or a specific keyword
                # Assuming LMMInterface is updated to handle a dictionary for audio_data
                # or a new parameter like 'transcribed_speech'
                llm_audio_input = {"type": "speech_transcript", "content": transcribed_text}

                self._log_info(f"Sending transcribed text to LMM: {llm_audio_input}")
                analysis = self.llm_interface.process_data(audio_data=llm_audio_input)

                if analysis:
                    self._log_info(f"LMM analysis from audio: {analysis}")
                    if self.intervention_engine:
                        suggestion = self.llm_interface.get_intervention_suggestion(analysis)
                        if suggestion:
                            self._log_info(f"Intervention suggested by LMM based on audio: {suggestion}")
                            # self.intervention_engine.trigger_intervention(suggestion["type"], suggestion.get("message"))
                            # Triggering intervention directly here might be too much.
                            # The main loop in main.py should probably handle fetching suggestions
                            # and deciding when/how to trigger them based on overall state.
                            # For now, we log that a suggestion was made.
                        else:
                            self._log_info("LMM processed audio, but no intervention suggested.")
                    else:
                        self._log_warning("Intervention engine not available to act on LMM suggestion from audio.")
                else:
                    self._log_info("LMM processed audio but returned no analysis.")
            else:
                self._log_warning("LMM interface not available to process transcribed text.")
        # else:
            # self._log_info("No new transcribed text from audio sensor this cycle.")
            # This can be noisy, so commented out. AudioSensor already logs if no text.

    def cleanup(self):
        """Called to release resources, e.g., when the application is closing."""
        self._log_info("LogicEngine cleaning up...")
        if self.audio_sensor:
            self.audio_sensor.release()
            self._log_info("AudioSensor released.")
        self._log_info("LogicEngine cleanup complete.")


if __name__ == '__main__':
    # --- Mocking dependencies for testing LogicEngine with STT ---
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
        def trigger_intervention(self, type, message=None):
            print(f"MOCK_INTERVENTION: Triggered type='{type}', message='{message or ''}'")

    mock_logger = MockDataLogger()
    mock_lmm = MockLMMInterface()
    mock_intervention_engine = MockInterventionEngine()

    # Ensure config.VOSK_MODEL_PATH is set or AudioSensor will run without STT
    # For this test, we assume it's set and the model exists, or AudioSensor handles it.
    print(f"Using VOSK_MODEL_PATH from config: '{config.VOSK_MODEL_PATH}' for test.")
    import os
    if not os.path.exists(config.VOSK_MODEL_PATH):
         print(f"WARNING: Vosk model not found at '{config.VOSK_MODEL_PATH}'. STT part of test may not function fully.")


    engine = LogicEngine(data_logger=mock_logger, llm_interface=mock_lmm, intervention_engine=mock_intervention_engine)

    def test_callback(new_mode, old_mode):
        print(f"Test Callback: Mode changed from {old_mode} to {new_mode}")
    engine.tray_callback = test_callback

    print(f"\nInitial mode: {engine.get_mode()}")
    assert engine.get_mode() == "active" # Should be active by default

    # --- Test STT processing loop ---
    if engine.audio_sensor and not (engine.audio_sensor.has_error() and "Vosk init failed" in engine.audio_sensor.get_last_error()):
        print("\n--- Testing STT processing. Speak 'hello' into your microphone. ---")
        print("Will run process_audio_input() for 10 cycles (approx 10-15 seconds).")
        engine.set_mode("active") # Ensure active mode for STT
        for i in range(10):
            print(f"Audio processing cycle {i+1}...")
            engine.process_audio_input()
            time.sleep(1) # Wait for audio chunk and processing

        # Try a final transcription call (might not always yield more if continuously processing)
        if engine.audio_sensor:
            final_text, _ = engine.audio_sensor.get_final_transcription()
            if final_text:
                 print(f"Final transcription attempt from sensor: {final_text}")
                 # Potentially send this to LMM too if it's different or more complete
                 llm_audio_input = {"type": "speech_transcript_final", "content": final_text}
                 analysis = engine.llm_interface.process_data(audio_data=llm_audio_input)
                 if analysis:
                     suggestion = engine.llm_interface.get_intervention_suggestion(analysis)
                     if suggestion:
                         print(f"LMM suggestion from final audio: {suggestion}")
                         # engine.intervention_engine.trigger_intervention(suggestion["type"], suggestion.get("message"))

    else:
        print("\n--- STT processing test SKIPPED (AudioSensor init failed or Vosk model issue) ---")


    # --- Original mode switching tests (should still work) ---
    print("\n--- Testing mode switching ---")
    engine.set_mode("active") # Reset
    engine.cycle_mode()
    print(f"Mode after cycle 1: {engine.get_mode()}")

    engine.toggle_pause_resume()
    print(f"Mode after pause: {engine.get_mode()}")

    engine.toggle_pause_resume()
    print(f"Mode after resume: {engine.get_mode()}")

    print("\nSimulating snooze duration passing...")
    engine.snooze_end_time = time.time() - 1
    print(f"Mode after snooze expired (on next get_mode call): {engine.get_mode()}")
    assert engine.current_mode == "active"

    engine.cleanup()
    print("\nLogicEngine tests complete.")
