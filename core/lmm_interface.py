# LMM Interface
# This module is responsible for interacting with a Large Language Model (LMM).

import config
import requests
import json
import re
import time
from typing import Optional, Dict, Any, List

class LMMInterface:
    SYSTEM_INSTRUCTION = """
    You are an autonomous co-regulator. Analyze the provided sensor metrics and context to estimate the user's state.

    Output a valid JSON object with the following structure:
    {
      "state_estimation": {
        "arousal": <int 0-100>,
        "overload": <int 0-100>,
        "focus": <int 0-100>,
        "energy": <int 0-100>,
        "mood": <int 0-100>
      },
      "suggestion": {
        "id": "<intervention_id_string_from_library>",
        "type": "<intervention_type_string_fallback>",
        "message": "<text_to_speak_to_user_fallback>"
      }
    }

    If no intervention is needed, set "suggestion" to null.

    Available Interventions (by ID):
    [Physiology]: box_breathing, shoulder_drop, eye_strain_release, arousal_redirect
    [Sensory]: audio_grounding, visual_scan, cold_water
    [Cognitive]: context_switch, reality_check, task_chunking, doom_scroll_breaker
    [Creative]: content_pivot, sultry_persona_prompt, public_persona_prompt

    If you suggest one of these, use its exact ID in the "id" field. You may omit "message" if using an ID, as the system will handle the sequence.
    If you need a custom ad-hoc intervention, leave "id" null and provide "type" and "message".

    Ensure your response is ONLY valid JSON, no markdown formatting.
    """

    def __init__(self, data_logger=None):
        """
        Initializes the LMMInterface.
        - data_logger: An instance of DataLogger for logging.
        """
        self.logger = data_logger
        # Ensure URL ends with v1/chat/completions for OpenAI compatibility
        base_url = config.LOCAL_LLM_URL.rstrip('/')
        if not base_url.endswith("/v1/chat/completions"):
             self.llm_url = f"{base_url}/v1/chat/completions"
        else:
             self.llm_url = base_url

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
        elif self.logger and hasattr(self.logger, 'log_level') and self.logger.log_level == "DEBUG":
             self.logger.log_info(f"LMMInterface-DEBUG: {message}")

    def check_connection(self) -> bool:
        """Checks if the LMM server is reachable."""
        try:
            # Try a simple models list check if available, or just a dummy completion
            # Usually /v1/models is standard
            models_url = self.llm_url.replace("/chat/completions", "/models")
            response = requests.get(models_url, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    def _validate_response_schema(self, data: Any) -> bool:
        """
        Validates the structure of the LMM response.
        Expected:
        {
            "state_estimation": { "arousal": int, ... },
            "suggestion": dict or None
        }
        """
        if not isinstance(data, dict):
            return False

        # Check state_estimation
        state = data.get("state_estimation")
        if not isinstance(state, dict):
            self._log_warning(f"Validation Error: 'state_estimation' missing or not a dict. Got: {type(state)}")
            return False

        required_keys = ["arousal", "overload", "focus", "energy", "mood"]
        for key in required_keys:
            if key not in state:
                self._log_warning(f"Validation Error: Missing state key '{key}'")
                return False
            val = state[key]
            if not isinstance(val, (int, float)):
                self._log_warning(f"Validation Error: State key '{key}' is not a number. Got: {val}")
                return False
            if not (0 <= val <= 100):
                self._log_warning(f"Validation Error: State key '{key}' out of bounds (0-100). Got: {val}")
                return False

        # Check suggestion (optional but must be dict or None)
        suggestion = data.get("suggestion")
        if suggestion is not None and not isinstance(suggestion, dict):
             self._log_warning(f"Validation Error: 'suggestion' is not a dict or None. Got: {type(suggestion)}")
             return False

        return True

    def process_data(self, video_data=None, audio_data=None, user_context=None) -> Optional[Dict[str, Any]]:
        """
        Processes incoming sensor data and user context by sending it to the local LMM
        using an OpenAI-compatible chat completion endpoint.

        Args:
            video_data: Base64 encoded image data from the video sensor.
            audio_data: Data from the audio sensor (list of floats).
            user_context: Additional context dictionary (includes metrics).

        Returns:
            A dictionary with the LMM's response or None on failure.
        """
        self._log_info("Sending data to local LMM...")

        if video_data is None and audio_data is None and not user_context:
            self._log_warning("No data provided to LMM process_data.")
            return None

        # Construct User Message
        content_parts = []

        # 1. Text Context & Metrics
        context_str = "Analyze the following user status:\n"
        if user_context:
            context_str += f"Current Mode: {user_context.get('current_mode', 'unknown')}\n"
            context_str += f"Trigger Reason: {user_context.get('trigger_reason', 'unknown')}\n"
            metrics = user_context.get('sensor_metrics', {})
            context_str += f"Audio Level (RMS): {metrics.get('audio_level', 0.0):.4f}\n"
            context_str += f"Video Activity (Motion): {metrics.get('video_activity', 0.0):.2f}\n"

            est = user_context.get('current_state_estimation')
            if est:
                 context_str += f"Previous State: {est}\n"

        content_parts.append({"type": "text", "text": context_str})

        # 2. Image (Video Frame)
        if video_data:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{video_data}"
                }
            })

        # Payload
        payload = {
            "model": config.LOCAL_LLM_MODEL_ID,
            "messages": [
                {"role": "system", "content": self.SYSTEM_INSTRUCTION},
                {"role": "user", "content": content_parts}
            ],
            "temperature": 0.2, # Low temp for consistent JSON
            "max_tokens": 500
        }

        # Retry logic
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(self.llm_url, json=payload, timeout=20)
                response.raise_for_status()

                response_json = response.json()
                content = response_json['choices'][0]['message']['content']

                # Clean content (remove markdown code blocks if present)
                clean_content = self._clean_json_string(content)

                parsed_result = json.loads(clean_content)

                # Validation Step
                if self._validate_response_schema(parsed_result):
                    self._log_info(f"Received valid JSON from LMM.")
                    self._log_debug(f"LMM Response: {parsed_result}")
                    return parsed_result
                else:
                    self._log_error(f"Response failed schema validation.", details=f"Parsed: {parsed_result}")
                    # If schema is wrong, retrying might not help unless LLM hallucinated.
                    # We continue loop to try again with a fresh generation.

            except requests.exceptions.RequestException as e:
                self._log_warning(f"Connection error (Attempt {attempt+1}/{retries}): {e}")
                time.sleep(1)
            except json.JSONDecodeError as e:
                self._log_error(f"Failed to parse JSON response: {e}", details=f"Raw content: {content}")
                # Retry allows chance for better formatting next time
                time.sleep(0.5)
            except KeyError as e:
                self._log_error(f"Unexpected response structure: {e}", details=f"Response: {response_json}")
                time.sleep(0.5)

        self._log_error(f"Failed to get valid response from LMM after {retries} attempts.")
        return None

    def _clean_json_string(self, text):
        """Removes markdown code blocks and whitespace."""
        # Remove ```json ... ``` or ``` ... ```
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```$', '', text, flags=re.MULTILINE)
        return text.strip()

    def get_intervention_suggestion(self, processed_analysis):
        """
        Extracts an intervention suggestion from the LMM's analysis.
        """
        if not processed_analysis:
            return None
        return processed_analysis.get("suggestion")

if __name__ == '__main__':
    # Test suite
    class MockDataLogger:
        def __init__(self) -> None:
            self.log_level = "DEBUG"
        def log_info(self, msg: str) -> None:
            print(f"INFO: {msg}")
        def log_warning(self, msg: str) -> None:
            print(f"WARN: {msg}")
        def log_error(self, msg: str, details: str = "") -> None:
            print(f"ERROR: {msg} | Details: {details}")
        def log_debug(self, msg: str) -> None:
            print(f"DEBUG: {msg}")

    mock_logger = MockDataLogger()
    lmm_interface = LMMInterface(data_logger=mock_logger)

    # Verify URL construction
    expected_url = config.LOCAL_LLM_URL.rstrip('/') + "/v1/chat/completions"
    if lmm_interface.llm_url != expected_url:
        print(f"FAILED: URL construction. Got {lmm_interface.llm_url}, expected {expected_url}")
    else:
        print(f"PASSED: URL construction: {lmm_interface.llm_url}")

    # Mock requests
    def mock_post_valid(url, json=None, timeout=None):
        import json as json_module
        response_content = {
            "state_estimation": {"arousal": 50, "overload": 20, "focus": 80, "energy": 60, "mood": 50},
            "suggestion": None
        }
        class MockResponse:
            def json(self):
                return {
                    "choices": [{
                        "message": {
                            "content": f"```json\n{json_module.dumps(response_content)}\n```"
                        }
                    }]
                }
            def raise_for_status(self): pass
        return MockResponse()

    requests.post = mock_post_valid

    print("\n--- Test 1: Valid Response ---")
    res1 = lmm_interface.process_data(user_context={"sensor_metrics": {"audio_level": 0.1}})
    if res1 and res1["suggestion"] is None:
        print("PASSED: Valid response parsed.")
    else:
        print(f"FAILED: Result: {res1}")

    print("\n--- Test 2: Invalid Schema (Missing Key) ---")
    def mock_post_invalid_key(url, json=None, timeout=None):
        import json as json_module
        response_content = {
            "state_estimation": {"arousal": 50}, # Missing others
            "suggestion": None
        }
        class MockResponse:
            def json(self):
                return {
                    "choices": [{
                        "message": {
                            "content": f"{json_module.dumps(response_content)}"
                        }
                    }]
                }
            def raise_for_status(self): pass
        return MockResponse()

    requests.post = mock_post_invalid_key
    # Provide minimal context to pass the "No data provided" check
    res2 = lmm_interface.process_data(user_context={"sensor_metrics": {}})
    if res2 is None:
        print("PASSED: Invalid schema rejected.")
    else:
        print(f"FAILED: Invalid schema accepted. Result: {res2}")

    print("\n--- Test 3: Invalid Schema (Out of Bounds) ---")
    def mock_post_invalid_bounds(url, json=None, timeout=None):
        import json as json_module
        response_content = {
            "state_estimation": {"arousal": 150, "overload": 0, "focus": 0, "energy": 0, "mood": 0},
            "suggestion": None
        }
        class MockResponse:
            def json(self):
                return {
                    "choices": [{
                        "message": {
                            "content": f"{json_module.dumps(response_content)}"
                        }
                    }]
                }
            def raise_for_status(self): pass
        return MockResponse()

    requests.post = mock_post_invalid_bounds
    # Provide minimal context to pass the "No data provided" check
    res3 = lmm_interface.process_data(user_context={"sensor_metrics": {}})
    if res3 is None:
        print("PASSED: Out of bounds value rejected.")
    else:
        print(f"FAILED: Out of bounds value accepted. Result: {res3}")

