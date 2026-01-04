import requests
import json
import re
import time
from typing import Optional, Dict, Any, TypedDict, List
import config
from .intervention_library import InterventionLibrary
import config
from typing import Optional, Dict, Any, List, TypedDict, Union
from .intervention_library import InterventionLibrary
from .prompts.v1 import SYSTEM_INSTRUCTION_V1

# Define schema types for better clarity and future validation

# Define response structures for type hinting
class StateEstimation(TypedDict):
    arousal: int
    overload: int
    focus: int
    energy: int
    mood: int

class Suggestion(TypedDict, total=False):
    id: Optional[str]
    type: Optional[str]
    message: Optional[str]

class LMMResponse(TypedDict):
    state_estimation: StateEstimation
    visual_context: Optional[List[str]]
    suggestion: Optional[Suggestion]
    _meta: Optional[Dict[str, Any]] # For internal flags like is_fallback

class LMMInterface:
    BASE_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_V1

    def __init__(self, data_logger=None, intervention_library: Optional[InterventionLibrary] = None):
        """
        Initializes the LMMInterface.
        - data_logger: An instance of DataLogger for logging.
        - intervention_library: Optional InterventionLibrary instance.
        """
        self.logger = data_logger

        # Initialize Intervention Library
        self.intervention_library = intervention_library if intervention_library else InterventionLibrary()

        # Construct System Instruction
        interventions_info = self.intervention_library.get_all_interventions_info()
        self.SYSTEM_INSTRUCTION = self.BASE_SYSTEM_INSTRUCTION.replace("{interventions_list}", interventions_info)

        # Ensure URL ends with v1/chat/completions for OpenAI compatibility
        base_url = config.LOCAL_LLM_URL.rstrip('/')
        if not base_url.endswith("/v1/chat/completions"):
             self.llm_url = f"{base_url}/v1/chat/completions"
        else:
             self.llm_url = base_url

        # Circuit Breaker State
        self.circuit_failures = 0
        self.circuit_open_time = 0
        self.circuit_max_failures = getattr(config, 'LMM_CIRCUIT_BREAKER_MAX_FAILURES', 5)
        self.circuit_cooldown = getattr(config, 'LMM_CIRCUIT_BREAKER_COOLDOWN', 60)

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
            "visual_context": ["tag", ...], # Optional
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

        # Check visual_context (Optional, but if present must be list of strings)
        visual_context = data.get("visual_context")
        if visual_context is not None:
            if not isinstance(visual_context, list):
                self._log_warning(f"Validation Error: 'visual_context' is not a list. Got: {type(visual_context)}")
                return False
            if not all(isinstance(item, str) for item in visual_context):
                self._log_warning(f"Validation Error: 'visual_context' contains non-string items.")
                return False

        # Check suggestion (optional but must be dict or None)
        suggestion = data.get("suggestion")
        if suggestion is not None and not isinstance(suggestion, dict):
             self._log_warning(f"Validation Error: 'suggestion' is not a dict or None. Got: {type(suggestion)}")
             return False

        return True

    def _get_fallback_response(self) -> LMMResponse:
        """Returns a safe, neutral response when the LMM is unavailable."""
        return {
            "state_estimation": {
                "arousal": 50,
                "overload": 0,
                "focus": 50,
                "energy": 50,
                "mood": 50
            },
            "visual_context": [],
            "suggestion": None,
            "_meta": {"is_fallback": True}
        }

    def _clean_json_string(self, text):
        """Removes markdown code blocks and whitespace."""
        # Remove ```json ... ``` or ``` ... ```
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```$', '', text, flags=re.MULTILINE)
        return text.strip()

    def _send_request_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends request to LMM with manual retry logic."""
        retries = 3
        backoff = 2
        last_exception = None

        for attempt in range(retries):
            try:
                response = requests.post(self.llm_url, json=payload, timeout=20)
                response.raise_for_status()

                response_json = response.json()
                content = response_json['choices'][0]['message']['content']
                clean_content = self._clean_json_string(content)

                try:
                    parsed_result = json.loads(clean_content)
                except json.JSONDecodeError as e:
                     raise ValueError(f"JSON decode error: {e}")

                if not self._validate_response_schema(parsed_result):
                    # If schema is invalid, we might want to retry if it's a transient generation error
                    # But for now, we'll treat it as a failure that might be retried
                    raise ValueError(f"Schema validation failed: {parsed_result}")

                return parsed_result

            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                last_exception = e
                self._log_warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2 # Exponential backoff

        if last_exception:
            raise last_exception
        raise Exception("Unknown error in _send_request_with_retry")

    def _get_fallback_response(self, user_context: Optional[Dict[str, Any]] = None) -> LMMResponse:
        """Returns a safe, neutral response when the LMM is unavailable, using simple heuristics."""

        fallback_state = {
            "arousal": 50,
            "overload": 0,
            "focus": 50,
            "energy": 50,
            "mood": 50
        }
        suggestion = None

        if user_context:
            metrics = user_context.get('sensor_metrics', {})
            audio_level = metrics.get('audio_level', 0.0)
            video_activity = metrics.get('video_activity', 0.0)

            if audio_level > 0.5:
                # Loud environment
                fallback_state["overload"] = 70
                # Try to match with an existing ID if possible, otherwise generic
                suggestion = {
                    "id": None, # Ad-hoc
                    "type": "text",
                    "message": "It's quite loud. Maybe take a moment of silence?"
                }

            elif video_activity > 20:
                # High activity
                fallback_state["arousal"] = 70
                suggestion = {
                    "id": None,
                    "type": "text",
                    "message": "You seem active. Remember to breathe."
                }

        return {
            "state_estimation": fallback_state,
            "suggestion": suggestion,
            "_meta": {"is_fallback": True}
        }

    def process_data(self, video_data=None, audio_data=None, user_context=None) -> Optional[LMMResponse]:
        """
        Processes incoming sensor data and user context by sending it to the local LMM.

        Args:
            video_data: Base64 encoded image data from the video sensor.
            audio_data: Data from the audio sensor (list of floats).
            user_context: Additional context dictionary (includes metrics).

        Returns:
            A dictionary with the LMM's response or None on failure.
        """
        self._log_info("Sending data to local LMM...")

        # Circuit Breaker Check
        if self.circuit_failures >= self.circuit_max_failures:
            if time.time() - self.circuit_open_time < self.circuit_cooldown:
                self._log_warning(f"Circuit breaker open. Skipping LMM call. (Cooldown: {self.circuit_cooldown}s)")
                if getattr(config, 'LMM_FALLBACK_ENABLED', False):
                    return self._get_fallback_response(user_context)
                return None
            else:
                self._log_info("Circuit breaker cooldown expired. Retrying connection.")
                self.circuit_failures = 0
                self.circuit_open_time = 0

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

            # Add detailed audio analysis if available
            audio_analysis = metrics.get('audio_analysis', {})
            if audio_analysis:
                context_str += f"Audio Pitch (est): {audio_analysis.get('pitch_estimation', 0.0):.2f} Hz\n"
                context_str += f"Audio Pitch Variance: {audio_analysis.get('pitch_variance', 0.0):.2f}\n"
                context_str += f"Audio ZCR: {audio_analysis.get('zcr', 0.0):.4f}\n"
                context_str += f"Speech Rate (Burst Density): {audio_analysis.get('activity_bursts', 0)}\n"

            context_str += f"Video Activity (Motion): {metrics.get('video_activity', 0.0):.2f}\n"

            # Add detailed video/face analysis (Posture)
            video_analysis = metrics.get('video_analysis', {})
            if video_analysis and video_analysis.get("face_detected"):
                context_str += f"Face Detected: Yes\n"
                context_str += f"Face Size Ratio: {video_analysis.get('face_size_ratio', 0.0):.3f} (Lean/Focus)\n"
                context_str += f"Face Vertical Pos: {video_analysis.get('vertical_position', 0.0):.2f} (0=Top, 1=Bottom)\n"
            else:
                context_str += f"Face Detected: No\n"

            est = user_context.get('current_state_estimation')
            if est:
                 context_str += f"Previous State: {est}\n"

            # Add suppressed interventions
            suppressed = user_context.get('suppressed_interventions')
            if suppressed:
                context_str += f"\nSuppressed Interventions (Do NOT suggest): {', '.join(suppressed)}\n"

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

        try:
            result = self._send_request_with_retry(payload)
            self._log_info(f"Received valid JSON from LMM.")
            self._log_debug(f"LMM Response: {result}")
            # Reset circuit breaker on success
            self.circuit_failures = 0
            return result

        except Exception as e:
            self._log_error(f"LMM Request Failed after retries: {e}")

            # Increment Circuit Breaker
            self.circuit_failures += 1
            if self.circuit_failures >= self.circuit_max_failures:
                 self.circuit_open_time = time.time()
                 self._log_warning(f"LMM Circuit Breaker TRIPPED. Pausing calls for {self.circuit_cooldown}s.")

            if getattr(config, 'LMM_FALLBACK_ENABLED', False):
                 self._log_info("LMM_FALLBACK_ENABLED is True. Returning neutral state.")
                 return self._get_fallback_response(user_context)

            return None
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
                    # Reset circuit breaker on success
                    self.circuit_failures = 0
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

        # Increment Circuit Breaker
        self.circuit_failures += 1
        if self.circuit_failures >= self.circuit_max_failures:
             self.circuit_open_time = time.time()
             self._log_warning(f"LMM Circuit Breaker TRIPPED. Pausing calls for {self.circuit_cooldown}s.")

        # Check for fallback
        if getattr(config, 'LMM_FALLBACK_ENABLED', False):
             self._log_info("LMM_FALLBACK_ENABLED is True. Returning neutral state.")
             return self._get_fallback_response()

        return None

    def get_intervention_suggestion(self, processed_analysis: LMMResponse) -> Optional[Dict[str, Any]]:
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
            "visual_context": ["person_sitting", "messy_room"],
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

    print("\n--- Test 1: Valid Response (with Visual Context) ---")
    res1 = lmm_interface.process_data(user_context={"sensor_metrics": {"audio_level": 0.1}})
    if res1 and res1["suggestion"] is None and "visual_context" in res1:
        print(f"PASSED: Valid response parsed. Visual Context: {res1['visual_context']}")
    else:
        print(f"FAILED: Result: {res1}")

    print("\n--- Test 2: Invalid Schema (Bad Visual Context) ---")
    def mock_post_invalid_context(url, json=None, timeout=None):
        import json as json_module
        response_content = {
            "state_estimation": {"arousal": 50, "overload": 20, "focus": 80, "energy": 60, "mood": 50},
            "visual_context": "this should be a list", # Error
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

    requests.post = mock_post_invalid_context
    # Disable fallback to check validation
    orig_fallback = config.LMM_FALLBACK_ENABLED
    config.LMM_FALLBACK_ENABLED = False

    res2 = lmm_interface.process_data(user_context={"sensor_metrics": {}})
    if res2 is None:
        print("PASSED: Invalid visual_context schema rejected.")
    else:
        print(f"FAILED: Invalid schema accepted. Result: {res2}")

    config.LMM_FALLBACK_ENABLED = orig_fallback
