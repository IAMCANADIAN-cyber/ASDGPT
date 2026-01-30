import sqlite3
import json
import datetime
import os
import config

class PersistentDataStore:
    def __init__(self, db_file_path=None):
        self.db_file_path = db_file_path or config.DATABASE_FILE
        # Ensure the directory for the database file exists
        db_dir = os.path.dirname(self.db_file_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir)
                print(f"PersistentDataStore: Created directory {db_dir}")
            except OSError as e:
                print(f"PersistentDataStore: Error creating directory {db_dir}: {e}. Using current directory for DB.")
                self.db_file_path = os.path.basename(self.db_file_path)

        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_file_path, check_same_thread=False) # check_same_thread=False for potential multi-threaded access from DataLogger
            print(f"PersistentDataStore: Connected to database {self.db_file_path}")
        except sqlite3.Error as e:
            print(f"PersistentDataStore: Error connecting to database {self.db_file_path}: {e}")
            # Potentially fallback to a in-memory DB or handle error appropriately
            self.conn = sqlite3.connect(":memory:", check_same_thread=False)
            print("PersistentDataStore: Connected to in-memory database as fallback.")

    def initialize_tables(self):
        if not self.conn:
            print("PersistentDataStore: No database connection, cannot initialize tables.")
            return

        try:
            cursor = self.conn.cursor()
            # Table for general events (like user feedback, interventions, sensor errors, etc.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data_json TEXT
                )
            """)
            # Future: Table for sensor readings (if high-frequency raw data needs storing)
            # cursor.execute("""
            #     CREATE TABLE IF NOT EXISTS sensor_readings (
            #         id INTEGER PRIMARY KEY AUTOINCREMENT,
            #         timestamp TEXT NOT NULL,
            #         sensor_type TEXT NOT NULL, -- e.g., 'audio_volume', 'video_activity'
            #         value REAL,
            #         metadata_json TEXT
            #     )
            # """)
            self.conn.commit()
            print("PersistentDataStore: Tables initialized (or already exist).")
        except sqlite3.Error as e:
            print(f"PersistentDataStore: Error initializing tables: {e}")

    def log_event(self, event_type: str, event_data: dict = None):
        if not self.conn:
            print(f"PersistentDataStore: No database connection, cannot log event: {event_type}")
            return

        timestamp = datetime.datetime.now().isoformat()
        event_data_json = json.dumps(event_data) if event_data else None

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, event_data_json)
                VALUES (?, ?, ?)
            """, (timestamp, event_type, event_data_json))
            self.conn.commit()
            # print(f"PersistentDataStore: Logged event '{event_type}'.") # Can be too noisy
        except sqlite3.Error as e:
            print(f"PersistentDataStore: Error logging event '{event_type}': {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            print(f"PersistentDataStore: Database connection to {self.db_file_path} closed.")

    def __del__(self):
        # Ensure connection is closed when the object is garbage collected
        self.close()

if __name__ == '__main__':
    # Basic testing for PersistentDataStore
    print("--- Testing PersistentDataStore ---")
    # Ensure config has DATABASE_FILE for testing
    if not hasattr(config, 'DATABASE_FILE'):
        config.DATABASE_FILE = "test_persistent_store.sqlite"
        print(f"Test: using {config.DATABASE_FILE}")

    # Clean up old test database if it exists
    if os.path.exists(config.DATABASE_FILE):
        os.remove(config.DATABASE_FILE)
        print(f"Test: Removed old {config.DATABASE_FILE}")

    store = PersistentDataStore()
    store.initialize_tables()

    # Test logging some events
    store.log_event("test_event_1", {"data": "sample_value", "id": 123})
    store.log_event("test_event_no_data")
    store.log_event("user_feedback", {"intervention_id": "posture_01", "rating": "helpful"})

    print(f"Test: Events logged. Check the database file: {store.db_file_path}")

    # Example: Querying the database to verify (optional here, manual check is fine for now)
    try:
        if store.conn:
            cursor = store.conn.cursor()
            cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 3")
            rows = cursor.fetchall()
            print("\nLast 3 events from DB:")
            for row in rows:
                print(row)
    except sqlite3.Error as e:
        print(f"Test: Error querying DB: {e}")

    store.close()
    print("--- PersistentDataStore test finished ---")
