import requests
import json
import re
import time
from typing import Optional, Dict, Any, TypedDict, List
import config
from .intervention_library import InterventionLibrary

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
    suggestion: Optional[Suggestion]

class LMMInterface:
    BASE_SYSTEM_INSTRUCTION = """
    You are an autonomous co-regulator. Analyze the provided sensor metrics and context to estimate the user's state.

    Sensor Interpretations:
    - Audio Level (RMS): High (>0.5) = Loud environment/speech. Low (<0.1) = Silence.
    - Video Activity: High (>20) = High movement/pacing. Low (<5) = Stillness.
    - Face Size Ratio: High (>0.15) = Leaning in/High Focus. Low (<0.05) = Leaning back/Distanced.
    - Vertical Position: High (>0.6) = Slouching/Low Energy. Low (<0.4) = Upright/High Energy.
    - Horizontal Position: Approx 0.5 is centered.

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
    {interventions_list}

    If you suggest one of these, use its exact ID in the "id" field. You may omit "message" if using an ID, as the system will handle the sequence.
    If you need a custom ad-hoc intervention, leave "id" null and provide "type" and "message".

    Ensure your response is ONLY valid JSON, no markdown formatting.
    """

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

                parsed_result = json.loads(clean_content)

                if not self._validate_response_schema(parsed_result):
                    raise ValueError(f"Schema validation failed: {parsed_result}")

                return parsed_result

            except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError, KeyError) as e:
                last_exception = e
                self._log_warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2 # Exponential backoff

        raise last_exception

    def process_data(self, video_data=None, audio_data=None, user_context=None) -> Optional[Dict[str, Any]]:
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
                context_str += f"Audio ZCR: {audio_analysis.get('zcr', 0.0):.4f}\n"

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
            return result
        except Exception as e:
            self._log_error(f"LMM Request Failed after retries: {e}")
            return self._fallback_response(user_context)

    def _fallback_response(self, user_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Generates a safe fallback response when the LMM is unavailable.
        """
        self._log_warning("Using fallback response mechanism.")

        # Simple rule-based fallback
        # If loud audio, suggest quiet
        # If high motion, suggest calm
        # Otherwise, just return neutral state

        metrics = user_context.get('sensor_metrics', {}) if user_context else {}
        audio_level = metrics.get('audio_level', 0.0)
        video_activity = metrics.get('video_activity', 0.0)

        # Default neutral state
        fallback_state = {
            "arousal": 50,
            "overload": 50,
            "focus": 50,
            "energy": 50,
            "mood": 50
        }

        suggestion = None

        if audio_level > 0.5:
            # Loud environment
            fallback_state["overload"] = 70
            # Try to match with an existing ID if possible, otherwise generic
            # Assuming 'gentle_reminder_text' exists in config
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
            "fallback": True # Flag to indicate this was a fallback
        }

    def get_intervention_suggestion(self, processed_analysis):
        """
        Extracts an intervention suggestion from the LMM's analysis.
        """
        if not processed_analysis:
            return None
        return processed_analysis.get("suggestion")
