import cv2
import time
import config # For CAMERA_INDEX

class VideoSensor:
    def __init__(self, camera_index=None, data_logger=None):
        self.camera_index = camera_index if camera_index is not None else config.CAMERA_INDEX
        self.logger = data_logger
        self.cap = None
        self.error_state = False
        self.last_error_message = ""
        self.retry_delay = 30  # seconds
        self.last_retry_time = 0

        self._initialize_capture()

    def _log_info(self, message):
        if self.logger: self.logger.log_info(f"VideoSensor: {message}")
        else: print(f"INFO: VideoSensor: {message}")

    def _log_warning(self, message):
        if self.logger: self.logger.log_warning(f"VideoSensor: {message}")
        else: print(f"WARNING: VideoSensor: {message}")

    def _log_error(self, message, details=""):
        full_message = f"VideoSensor: {message}"
        if self.logger: self.logger.log_error(full_message, details)
        else: print(f"ERROR: {full_message} | Details: {details}")
        self.last_error_message = message # Store the most recent error

    def _initialize_capture(self):
        self._log_info(f"Attempting to initialize video capture on index {self.camera_index}...")
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.error_state = True
                error_msg = f"Failed to open video capture on index {self.camera_index}."
                self._log_error(error_msg)
                # No return here, get_frame will handle retry if error_state is True
            else:
                self.error_state = False
                self.last_error_message = ""
                self._log_info(f"Video capture initialized successfully on index {self.camera_index}.")
                # You might want to read a frame here to confirm it works fully
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.error_state = True
                    error_msg = f"Successfully opened camera index {self.camera_index} but failed to read initial frame."
                    self._log_error(error_msg)
                    if self.cap: self.cap.release()
                    self.cap = None
                else:
                    self._log_info("Initial frame read successfully.")

        except Exception as e:
            self.error_state = True
            error_msg = f"Exception during video capture initialization on index {self.camera_index}."
            self._log_error(error_msg, str(e))
            if self.cap:
                self.cap.release()
            self.cap = None

        self.last_retry_time = time.time() # Set last_retry_time after an attempt

    def get_frame(self):
        if self.error_state:
            if time.time() - self.last_retry_time >= self.retry_delay:
                self._log_info("Attempting to re-initialize video capture due to previous error...")
                self._initialize_capture() # Attempt to re-initialize

            if self.error_state: # If still in error state after retry attempt
                return None, self.last_error_message # Indicate error and return last message
            # If re-initialization was successful, error_state is false, proceed to read frame

        if not self.cap or not self.cap.isOpened():
            # This case should ideally be caught by error_state, but as a safeguard:
            if not self.error_state: # If not already marked as error, something new happened
                self._log_error("Video capture is not open, though not in persistent error state.")
                self.error_state = True # Mark as error
            # No retry logic here, as it's handled by the error_state check at the beginning
            return None, "Video capture not available."

        try:
            ret, frame = self.cap.read()
            if not ret:
                self.error_state = True
                error_msg = "Failed to read frame from video capture."
                self._log_error(error_msg)
                return None, error_msg

            # If we successfully read a frame, ensure error_state is False
            if self.error_state: # Was in error, but now working
                self._log_info("Video sensor recovered and reading frames.")
                self.error_state = False
                self.last_error_message = ""

            return frame, None # Return frame and no error
        except Exception as e:
            self.error_state = True
            error_msg = "Exception while reading frame."
            self._log_error(error_msg, str(e))
            return None, error_msg

    def release(self):
        if self.cap and self.cap.isOpened():
            self._log_info("Releasing video capture device.")
            self.cap.release()
        self.cap = None
        self.error_state = False # Reset error state on explicit release

    def has_error(self):
        return self.error_state

    def get_last_error(self):
        return self.last_error_message

if __name__ == '__main__':
    # Example Usage (requires a webcam or will show errors)
    # Mock DataLogger for testing
    class MockDataLogger:
        def log_info(self, msg): print(f"MOCK_LOG_INFO: {msg}")
        def log_warning(self, msg): print(f"MOCK_LOG_WARN: {msg}")
        def log_error(self, msg, details=""): print(f"MOCK_LOG_ERROR: {msg} | Details: {details}")

    mock_logger = MockDataLogger()

    # Test with default camera index (usually 0)
    # Set a high index like 99 to test error case if you don't have multiple cameras
    # test_camera_index = 99
    test_camera_index = config.CAMERA_INDEX

    print(f"--- Testing VideoSensor with camera index {test_camera_index} ---")
    vs = VideoSensor(camera_index=test_camera_index, data_logger=mock_logger)

    if vs.has_error():
        print(f"Initial error: {vs.get_last_error()}")
        print(f"Will attempt retry after {vs.retry_delay} seconds if get_frame is called.")

    for i in range(5): # Try to get a few frames
        print(f"\nAttempting to get frame {i+1}...")
        frame, error = vs.get_frame()
        if error:
            print(f"Error getting frame: {error}")
            if vs.has_error() and i < 2 : # If error, wait for retry period for first couple of attempts
                 print(f"Sensor in error state. Waiting for {vs.retry_delay + 1}s to allow retry logic...")
                 time.sleep(vs.retry_delay +1)
            elif vs.has_error(): # If still erroring, don't wait full period for subsequent tests
                print("Sensor still in error state. Continuing test without long wait.")
                time.sleep(1)

        elif frame is not None:
            print(f"Frame {i+1} received successfully. Shape: {frame.shape}")
            # cv2.imshow("Test Frame", frame) # Uncomment to display frame
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #    break
            time.sleep(0.5) # Simulate some processing
        else:
            print(f"Frame {i+1} was None, but no explicit error string returned (should not happen). Has_Error: {vs.has_error()}")
            time.sleep(1)

    vs.release()
    # cv2.destroyAllWindows() # If imshow was used
    print("--- VideoSensor test finished ---")
