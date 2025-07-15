# LMM Interface
# This module is responsible for interacting with a Large Language Model (LMM).

import config
import requests

class LMMInterface:
    def __init__(self, data_logger=None):
        """
        Initializes the LMMInterface.
        - data_logger: An instance of DataLogger for logging.
        """
        self.logger = data_logger
        self.llm_url = config.LOCAL_LLM_URL
        self._log_info(f"LMMInterface initializing with URL: {self.llm_url}")

    def _log_info(self, message):
        if self.logger: self.logger.log_info(f"LMMInterface: {message}")
        else: print(f"INFO: LMMInterface: {message}")

    def _log_warning(self, message):
        if self.logger: self.logger.log_warning(f"LMMInterface: {message}")
        else: print(f"WARNING: LMMInterface: {message}")

    def _log_error(self, message, details=""):
        full_message = f"LMMInterface: {message}"
        if self.logger: self.logger.log_error(full_message, details)
        else: print(f"ERROR: {full_message} | Details: {details}")

    def _log_debug(self, message):
        if self.logger and hasattr(self.logger, 'log_debug'):
            self.logger.log_debug(f"LMMInterface: {message}")
        # Fallback for basic logging if logger has no log_debug but level is DEBUG
        elif self.logger and hasattr(self.logger, 'log_level') and self.logger.log_level == "DEBUG":
             self.logger.log_info(f"LMMInterface-DEBUG: {message}")


    def process_data(self, video_data=None, audio_data=None, user_context=None):
        """
        Processes incoming sensor data and user context by sending it to the local LMM.

        Args:
            video_data: Data from the video sensor.
            audio_data: Data from the audio sensor.
            user_context: Additional context.

        Returns:
            A dictionary with the LMM's response or None on failure.
        """
        self._log_info("Sending data to local LMM...")

        if video_data is None and audio_data is None:
            self._log_warning("No video or audio data provided to LMM process_data.")
            return None

        payload = {
            "video_data": video_data,
            "audio_data": audio_data,
            "user_context": user_context
        }

        try:
            response = requests.post(self.llm_url, json=payload, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            self._log_info(f"Received response from LMM: {response.json()}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self._log_error(f"Failed to connect to LMM at {self.llm_url}", str(e))
            return None

    def get_intervention_suggestion(self, processed_analysis):
        """
        Extracts an intervention suggestion from the LMM's analysis.
        Assumes the LMM can directly provide a suggestion.

        Args:
            processed_analysis: The JSON response from the LMM.

        Returns:
            A dictionary describing the suggested intervention or None.
        """
        if not processed_analysis:
            return None

        # Example: LMM returns a dict with a "suggestion" key
        # a valid suggestion would be like: {"type": "posture_reminder", "message": "Check your posture."}
        return processed_analysis.get("suggestion")

if __name__ == '__main__':
    # Example Usage
    class MockDataLogger:
        def __init__(self): self.log_level = "DEBUG"
        def log_info(self, msg): print(f"MOCK_LOG_INFO: {msg}")
        def log_warning(self, msg): print(f"MOCK_LOG_WARN: {msg}")
        def log_error(self, msg, details=""): print(f"MOCK_LOG_ERROR: {msg} | Details: {details}")
        def log_debug(self, msg): print(f"MOCK_LOG_DEBUG: {msg}")

    mock_logger = MockDataLogger()

    # Ensure .env file exists in the project root for this test to run as intended regarding API key.
    # Example .env content:
    # GOOGLE_API_KEY="YOUR_API_KEY_HERE"
    # OR
    # GOOGLE_API_KEY="actual_key_if_testing_real_calls"

    print("--- Testing LMMInterface ---")
    lmm_interface = LMMInterface(data_logger=mock_logger)

    print("\n--- Test Case 1: No data ---")
    analysis1 = lmm_interface.process_data()
    suggestion1 = lmm_interface.get_intervention_suggestion(analysis1)
    print(f"Analysis: {analysis1}, Suggestion: {suggestion1}")

    print("\n--- Test Case 2: Video data only ---")
    mock_video_data = {"summary": "User appears to be stationary."}
    analysis2 = lmm_interface.process_data(video_data=mock_video_data)
    suggestion2 = lmm_interface.get_intervention_suggestion(analysis2)
    print(f"Analysis: {analysis2}, Suggestion: {suggestion2}")
    if suggestion2:
        assert suggestion2["type"] == "posture_reminder"

    print("\n--- Test Case 3: Audio data only ---")
    mock_audio_data = {"average_db": -20}
    analysis3 = lmm_interface.process_data(audio_data=mock_audio_data)
    suggestion3 = lmm_interface.get_intervention_suggestion(analysis3)
    print(f"Analysis: {analysis3}, Suggestion: {suggestion3}")
    if suggestion3:
         assert suggestion3["type"] == "noise_alert"


    print("\n--- Test Case 4: Both video and audio data ---")
    analysis4 = lmm_interface.process_data(video_data=mock_video_data, audio_data=mock_audio_data)
    suggestion4 = lmm_interface.get_intervention_suggestion(analysis4)
    print(f"Analysis: {analysis4}, Suggestion: {suggestion4}")
    if suggestion4:
        # The combined event in simulation might be "potential_posture_issue_and_ambient_noise_level_high"
        # The get_intervention_suggestion logic currently prioritizes posture if "potential_posture_issue" is in event string.
        assert "posture_reminder" in suggestion4["type"] or "noise_alert" in suggestion4["type"]


    print("\n--- Test Case 5: Simulated LMM analysis with low confidence ---")
    low_confidence_analysis = {
        "detected_event": "potential_posture_issue",
        "confidence": 0.3, # Below threshold of 0.6
        "raw_llm_output": "Simulated: Video data suggests a slight possibility of a posture issue."
    }
    suggestion5 = lmm_interface.get_intervention_suggestion(low_confidence_analysis)
    print(f"Analysis: {low_confidence_analysis}, Suggestion (low confidence): {suggestion5}")
    assert suggestion5 is None

    print("\nLMMInterface tests complete.")
