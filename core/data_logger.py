import datetime
import config
import os
from .persistent_data_store import PersistentDataStore # Added import

class DataLogger:
    def __init__(self, log_file_path=None):
        self.log_file_path = log_file_path or config.LOG_FILE
        # Ensure log directory exists if path is nested
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"Error creating log directory {log_dir}: {e}. Logging to current directory.")
                self.log_file_path = os.path.basename(self.log_file_path)

        self.log_level = config.LOG_LEVEL.upper()
        self._log("INFO", f"DataLogger initialized. Log level: {self.log_level}. Log file: {self.log_file_path}")

        # Initialize PersistentDataStore
        try:
            self.persistent_store = PersistentDataStore() # Uses config.DATABASE_FILE by default
            self.persistent_store.initialize_tables()
            self._log("INFO", f"PersistentDataStore initialized with DB: {self.persistent_store.db_file_path}")
        except Exception as e:
            self._log("ERROR", f"Failed to initialize PersistentDataStore: {e}")
            self.persistent_store = None


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
        Logs a structured event.
        Example: event_type="user_feedback", payload={"intervention_id": "xyz", "rating": "helpful"}
        """
        if self.log_level in ["INFO", "DEBUG"]: # Or a specific "EVENT" level if desired
            message = f"Event: {event_type} | Payload: {payload}"
            self._log("EVENT", message) # Log to text file as before

        # Also log to persistent store if available
        if self.persistent_store:
            try:
                self.persistent_store.log_event(event_type, payload)
            except Exception as e:
                self._log("ERROR", f"DataLogger: Failed to log event to persistent store: {e}")


if __name__ == '__main__':
    print("--- STARTING DataLogger Test Main ---") # New print
    # Test DataLogger
    # Ensure config.py has LOG_FILE, LOG_LEVEL, and DATABASE_FILE defined
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "test_app_log.txt"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"
    if not hasattr(config, 'DATABASE_FILE'): config.DATABASE_FILE = "test_datalogger_events.sqlite"
    print(f"Test Main: Using LOG_FILE={config.LOG_FILE}, DATABASE_FILE={config.DATABASE_FILE}") # New print

    # Clean up old test database if it exists for a clean test run
    if os.path.exists(config.DATABASE_FILE):
        print(f"Test Main: Removing old test database: {config.DATABASE_FILE}")
        os.remove(config.DATABASE_FILE)

    logger = DataLogger()
    logger.log_info("This is an info message.")
    logger.log_warning("This is a warning message.")
    logger.log_error("This is an error message.", "Some additional details here.")
    logger.log_debug("This is a debug message. Will only show if LOG_LEVEL is DEBUG.")

    logger.log_event("test_event", {"data": "sample_value", "id": 123})
    logger.log_event("another_event", {"info": "more data", "count": 5})

    # Test logging to a specific file (and thus different DB if config not overridden)
    # For this test, we'll assume custom_logger still uses the default config.DATABASE_FILE
    # or its own based on its log_file_path if PersistentDataStore was more complex.
    # Current PersistentDataStore always uses config.DATABASE_FILE or its override.
    # So, custom_logger's events will go to the same DB as logger's if db_file_path not given to PDS.
    # This is fine for this test.

    print(f"\nCheck '{config.LOG_FILE}' for regular log output.")
    print(f"Check database '{config.DATABASE_FILE}' for structured event logs.")

    # Verify events in the database
    if logger.persistent_store and logger.persistent_store.conn:
        print("\n--- Verifying events from database ---")
        try:
            cursor = logger.persistent_store.conn.cursor()
            cursor.execute("SELECT timestamp, event_type, event_data_json FROM events ORDER BY id DESC LIMIT 3")
            rows = cursor.fetchall()
            if rows:
                for row in reversed(rows): # Print in order of insertion for test
                    print(f"DB Event: {row[0]}, Type: {row[1]}, Data: {row[2]}")
            else:
                print("No events found in database for verification.")
        except Exception as e:
            print(f"Error querying database for verification: {e}")
    else:
        print("\nPersistent store not available for DB verification.")

    # custom_logger = DataLogger("custom_logs/custom.log") # This would create another DB if PDS was tied to file path
    # custom_logger.log_info("Info message in custom log.")

    print("\n--- Content of test_app_log.txt ---")
    try:
        with open(config.LOG_FILE, 'r') as f: # config.LOG_FILE should be "test_app_log.txt" here
            print(f.read())
    except Exception as e:
        print(f"Error reading log file {config.LOG_FILE}: {e}")
    print("--- END Content of test_app_log.txt ---")

    print("\n--- DataLogger test finished ---")
    print("--- SUCCESSFULLY COMPLETED DataLogger Test Main ---")
