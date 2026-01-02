import datetime
import config
import os
import json

class DataLogger:
    def __init__(self, log_file_path=None, events_file_path=None):
        self.log_file_path = log_file_path or config.LOG_FILE
        self.events_file_path = events_file_path or getattr(config, 'EVENTS_FILE', 'user_data/events.jsonl')

        # Ensure log directory exists if path is nested
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"Error creating log directory {log_dir}: {e}. Logging to current directory.")
                self.log_file_path = os.path.basename(self.log_file_path)

        # Ensure events directory exists
        events_dir = os.path.dirname(self.events_file_path)
        if events_dir and not os.path.exists(events_dir):
             try:
                os.makedirs(events_dir)
             except OSError as e:
                print(f"Error creating events directory {events_dir}: {e}.")

        self.log_level = config.LOG_LEVEL.upper()
        self._log("INFO", f"DataLogger initialized. Log level: {self.log_level}. Log file: {self.log_file_path}")

    def _get_timestamp(self):
        return datetime.datetime.now().isoformat()

    def _log(self, level, message):
        timestamp = self._get_timestamp()
        log_entry = f"{timestamp} [{level}] {message}"
        print(log_entry) # Also print to console for immediate visibility

        try:
            with open(self.log_file_path, "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"CRITICAL: Failed to write to log file {self.log_file_path}: {e}")

    def log_info(self, message):
        if self.log_level in ["INFO", "DEBUG"]:
            self._log("INFO", message)

    def log_warning(self, message):
        if self.log_level in ["INFO", "DEBUG", "WARNING"]:
            self._log("WARNING", message)

    def log_error(self, message, details=""):
        full_message = f"{message} | Details: {details}" if details else message
        # Errors are always logged regardless of configured level
        self._log("ERROR", full_message)

    def log_debug(self, message):
        if self.log_level == "DEBUG":
            self._log("DEBUG", message)

    def log_event(self, event_type, payload):
        """
        Logs a structured event to a JSONL file.
        Example: event_type="user_feedback", payload={"intervention_id": "xyz", "rating": "helpful"}
        """
        # Also log to main log for context
        if self.log_level in ["INFO", "DEBUG"]:
            message = f"Event: {event_type} | Payload: {payload}"
            self._log("EVENT", message)

        # Write to events.jsonl
        event_entry = {
            "timestamp": self._get_timestamp(),
            "event_type": event_type,
            "payload": payload
        }

        try:
            with open(self.events_file_path, "a") as f:
                f.write(json.dumps(event_entry) + "\n")
        except Exception as e:
            self._log("ERROR", f"Failed to write event to {self.events_file_path}: {e}")


if __name__ == '__main__':
    # Test DataLogger
    # Ensure config.py has LOG_FILE and LOG_LEVEL defined
    # Example: LOG_FILE = "test_acr_log.txt", LOG_LEVEL = "DEBUG"
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "test_app_log.txt"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"
    if not hasattr(config, 'EVENTS_FILE'): config.EVENTS_FILE = "test_events.jsonl"

    logger = DataLogger()
    logger.log_info("This is an info message.")
    logger.log_warning("This is a warning message.")
    logger.log_error("This is an error message.", "Some additional details here.")
    logger.log_debug("This is a debug message. Will only show if LOG_LEVEL is DEBUG.")

    logger.log_event("test_event", {"data": "sample_value", "id": 123})

    # Test logging to a specific file
    custom_logger = DataLogger("custom_logs/custom.log")
    custom_logger.log_info("Info message in custom log.")

    print(f"Check '{config.LOG_FILE}', '{config.EVENTS_FILE}' and 'custom_logs/custom.log' for output.")
