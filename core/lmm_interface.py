import requests
import json
import re
import time
from typing import Optional, Dict, Any, List, TypedDict, Union
from typing import Optional, Dict, Any, TypedDict, List
import config
from .intervention_library import InterventionLibrary
from .prompts.v1 import SYSTEM_INSTRUCTION_V1

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
    _meta: Optional[Dict[str, Any]] # For internal flags like is_fallback, latency_ms

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
        if suggestion is not None:
            if not isinstance(suggestion, dict):
                 self._log_warning(f"Validation Error: 'suggestion' is not a dict or None. Got: {type(suggestion)}")
                 return False

            # Validate suggestion type if library is available
            s_type = suggestion.get("type")
            if s_type and self.intervention_library:
                # We can't strictly validate ID because LMM might suggest ad-hoc or fallback types
                # But we can check if it looks sane.
                # For now, just ensure 'type' is a string if present
                if not isinstance(s_type, str):
                    self._log_warning(f"Validation Error: 'suggestion.type' is not a string.")
                    return False

                # Check message presence if type implies it (generic 'text')
                if s_type == "text" and not suggestion.get("message"):
                     self._log_warning(f"Validation Error: 'suggestion' of type 'text' missing 'message'.")
                     return False

            # If suggestion object is present, it should ideally have 'type' or 'id'
            if not s_type and not suggestion.get("id"):
                self._log_warning(f"Validation Error: 'suggestion' missing both 'id' and 'type'.")
                return False

        return True

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

        # Enforce JSON mode if not already set, to ensure consistent output
        if "response_format" not in payload:
            payload["response_format"] = {"type": "json_object"}

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
                     # This is a content error, might be fixed by regeneration, so we treat it as retryable
                     raise ValueError(f"JSON decode error: {e}")

                if not self._validate_response_schema(parsed_result):
                    # If schema is invalid, we might want to retry if it's a transient generation error
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
            "visual_context": [],
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

            # Inject Active Window Context
            active_window = user_context.get('active_window')
            if active_window and active_window != "Unknown":
                context_str += f"Active Window: {active_window}\n"

            metrics = user_context.get('sensor_metrics', {})
            context_str += f"Audio Level (RMS): {metrics.get('audio_level', 0.0):.4f}\n"

            # Add detailed audio analysis if available
            audio_analysis = metrics.get('audio_analysis', {})
            if audio_analysis:
                context_str += f"Audio Pitch (est): {audio_analysis.get('pitch_estimation', 0.0):.2f} Hz\n"
                context_str += f"Audio Pitch Variance: {audio_analysis.get('pitch_variance', 0.0):.2f}\n"
                context_str += f"Audio ZCR: {audio_analysis.get('zcr', 0.0):.4f}\n"

                speech_rate = audio_analysis.get('speech_rate', 0.0)
                context_str += f"Speech Rate: {speech_rate:.2f} syllables/sec\n"

                is_speech = audio_analysis.get('is_speech', False)
                speech_conf = audio_analysis.get('speech_confidence', 0.0)
                context_str += f"Voice Activity: {'Yes' if is_speech else 'No'} (Conf: {speech_conf:.2f})\n"

            context_str += f"Video Activity (Motion): {metrics.get('video_activity', 0.0):.2f}\n"

            # Add detailed video/face analysis (Posture)
            video_analysis = metrics.get('video_analysis', {})
            if video_analysis and video_analysis.get("face_detected"):
                context_str += f"Face Detected: Yes\n"
                context_str += f"Face Size Ratio: {video_analysis.get('face_size_ratio', 0.0):.3f} (Lean/Focus)\n"
                context_str += f"Face Vertical Pos: {video_analysis.get('vertical_position', 0.0):.2f} (0=Top, 1=Bottom)\n"

                posture = video_analysis.get("posture_state")
                if posture and posture != "neutral":
                    context_str += f"Posture: {posture}\n"

                roll = video_analysis.get("face_roll_angle")
                if roll and abs(roll) > 15:
                    context_str += f"Head Tilt: {roll:.1f} deg\n"
            else:
                context_str += f"Face Detected: No\n"

            est = user_context.get('current_state_estimation')
            if est:
                 context_str += f"Previous State: {est}\n"

            # Add suppressed interventions
            suppressed = user_context.get('suppressed_interventions')
            if suppressed:
                context_str += f"\nSuppressed Interventions (Do NOT suggest): {', '.join(suppressed)}\n"

            # Add System Alerts (High Priority)
            alerts = user_context.get('system_alerts', [])
            if alerts:
                context_str += f"\nSYSTEM ALERTS (High Priority): {', '.join(alerts)}\n"
            # Add preferred interventions
            preferred = user_context.get('preferred_interventions')
            if preferred:
                context_str += f"\nPreferred Interventions (User found these helpful recently): {', '.join(preferred)}\n"

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
            start_time = time.time()
            result = self._send_request_with_retry(payload)
            latency_ms = (time.time() - start_time) * 1000

            # Inject latency into _meta
            if "_meta" not in result or result["_meta"] is None:
                result["_meta"] = {}
            result["_meta"]["latency_ms"] = latency_ms

            self._log_info(f"Received valid JSON from LMM. Latency: {latency_ms:.2f}ms")
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

    def get_intervention_suggestion(self, processed_analysis: LMMResponse) -> Optional[Dict[str, Any]]:
        """
        Extracts an intervention suggestion from the LMM's analysis.
        """
        if not processed_analysis:
            return None
        return processed_analysis.get("suggestion")
