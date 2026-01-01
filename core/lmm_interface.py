# LMM Interface
# This module is responsible for interacting with a Large Language Model (LMM).

import config
import requests
import json
import re
import time

class LMMInterface:
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

    def check_connection(self):
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

    def process_data(self, video_data=None, audio_data=None, user_context=None):
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

        # System Instruction
        system_instruction = """
        You are an autonomous co-regulator acting as a "Guardian Angel" and "Creative Director" for the user (Austin).
        Analyze the provided sensor metrics, video frame (if available), and context to estimate the user's state and recommend interventions.

        **Roles & Objectives:**
        1. **Guardian Angel:** Monitor for stress, tics, and escapism (doom-scrolling). Provide behavioral interventions.
        2. **Creative Director:** Analyze environment/mood for content creation opportunities (Private/Sultry vs. Public/Safe).

        **Context Detection (Vision):**
        - **Health:** Posture (slouching?), Face (distress, fatigue?), Tics (twitching?).
        - **Context:** Holding phone? (Doom-scrolling risk). Room state (messy vs. aesthetic?). Clothing (shirtless vs. dressed?).

        **Intervention Triggers:**
        - **Doom-Scroll Breaker:** Phone in hand > 15m, zoned out. -> Suggest ID: "doom_scroll_breaker"
        - **Arousal Redirect:** High arousal, phone usage, procrastination. -> Suggest ID: "arousal_redirect"
        - **Content Pivot:** High energy/arousal, messy room. -> Suggest ID: "content_pivot"
        - **Sultry Persona:** Shirtless/undressed, moody lighting, "thirst trap" vibes. -> Suggest ID: "sultry_persona_prompt"
        - **Public Persona:** Well-groomed, working, sharp. -> Suggest ID: "public_persona_prompt"

        Output a valid JSON object with the following structure:
        {
          "state_estimation": {
            "arousal": <int 0-100>,
            "overload": <int 0-100>,
            "focus": <int 0-100>,
            "energy": <int 0-100>,
            "mood": <int 0-100>
          },
          "context_detected": {
            "phone_usage": <bool>,
            "posture": "<good|slouching>",
            "room_state": "<tidy|messy>",
            "clothing": "<dressed|shirtless|underwear>"
          },
          "suggestion": {
            "type": "<intervention_id_from_library>",
            "message": "<reasoning_for_log_only>"
          }
        }

        *Note: The actual speech/action is handled by the system based on the ID. The 'message' here is just for your reasoning.*

        If no intervention is needed, set "suggestion" to null.
        Ensure your response is ONLY valid JSON, no markdown formatting.
        """

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
        # Note: We assume the local model supports vision if we send an image.
        # If it doesn't, this might error out depending on the backend,
        # but standard OpenAI format handles this.
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
                {"role": "system", "content": system_instruction},
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
                self._log_info(f"Received valid JSON from LMM.")
                self._log_debug(f"LMM Response: {parsed_result}")
                return parsed_result

            except requests.exceptions.RequestException as e:
                self._log_warning(f"Connection error (Attempt {attempt+1}/{retries}): {e}")
                time.sleep(1)
            except json.JSONDecodeError as e:
                self._log_error(f"Failed to parse JSON response: {e}", details=f"Raw content: {content}")
                # Don't retry immediately on parse error unless we want to try prompting again (out of scope)
                return None
            except KeyError as e:
                self._log_error(f"Unexpected response structure: {e}", details=f"Response: {response_json}")
                return None

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
    def mock_post(url, json, timeout):
        class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code
            def json(self):
                return self.json_data
            def raise_for_status(self):
                if self.status_code != 200:
                    raise requests.exceptions.RequestException("Mock Error")

        # Inspect payload
        messages = json['messages']
        user_content = messages[1]['content']

        has_text = any(p['type'] == 'text' for p in user_content)
        has_image = any(p['type'] == 'image_url' for p in user_content)

        # Simulate response based on content
        response_content = {
            "state_estimation": {"arousal": 50, "overload": 20, "focus": 80, "energy": 60, "mood": 50},
            "suggestion": None
        }

        if has_image:
             response_content["suggestion"] = {"type": "vision_check", "message": "I see you."}

        return MockResponse({
            "choices": [{
                "message": {
                    "content": f"```json\n{json.dumps(response_content)}\n```"
                }
            }]
        }, 200)

    # We need to import json in the mock scope or use the outer one, but since we are overriding requests.post
    # inside the test block, and 'json' argument name shadows the module 'json'.
    # I'll rename the argument to 'json_payload'.

    def mock_post_corrected(url, json=None, timeout=None):
        json_payload = json
        class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code
            def json(self):
                return self.json_data
            def raise_for_status(self):
                if self.status_code != 200:
                    raise requests.exceptions.RequestException("Mock Error")

        # Inspect payload
        messages = json_payload['messages']
        user_content = messages[1]['content']

        has_text = any(p['type'] == 'text' for p in user_content)
        has_image = any(p['type'] == 'image_url' for p in user_content)

        # Simulate response based on content
        response_content = {
            "state_estimation": {"arousal": 50, "overload": 20, "focus": 80, "energy": 60, "mood": 50},
            "suggestion": None
        }

        if has_image:
             response_content["suggestion"] = {"type": "vision_check", "message": "I see you."}

        import json as json_module
        return MockResponse({
            "choices": [{
                "message": {
                    "content": f"```json\n{json_module.dumps(response_content)}\n```"
                }
            }]
        }, 200)

    requests.post = mock_post_corrected

    print("\n--- Test 1: Text only ---")
    res1 = lmm_interface.process_data(user_context={"sensor_metrics": {"audio_level": 0.1}})
    if res1 and res1["suggestion"] is None:
        print("PASSED: Text only response parsed.")
    else:
        print(f"FAILED: Text only. Result: {res1}")

    print("\n--- Test 2: With Image ---")
    res2 = lmm_interface.process_data(video_data="base64str", user_context={})
    if res2 and res2["suggestion"] and res2["suggestion"]["type"] == "vision_check":
        print("PASSED: Image content handled.")
    else:
        print(f"FAILED: Image content. Result: {res2}")

    print("\n--- Test 3: JSON Parsing Error Handling ---")
    def mock_post_fail(url, json, timeout):
        return type('obj', (object,), {
            'json': lambda: {'choices': [{'message': {'content': 'Invalid JSON'}}]},
            'raise_for_status': lambda: None
        })
    requests.post = mock_post_fail
    res3 = lmm_interface.process_data(user_context={})
    if res3 is None:
        print("PASSED: Invalid JSON handled.")
    else:
        print(f"FAILED: Invalid JSON not handled. Result: {res3}")

