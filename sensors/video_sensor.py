import cv2
import time
import numpy as np
import collections

class VideoSensor:
    def __init__(self, camera_index=0, data_logger=None, history_size=5):
        self.camera_index = camera_index
        self.logger = data_logger
        self.cap = None
        self.last_frame = None

        # History buffers for smoothing
        self.history_size = history_size
        self.history = {
            "face_size_ratio": collections.deque(maxlen=history_size),
            "vertical_position": collections.deque(maxlen=history_size),
            "horizontal_position": collections.deque(maxlen=history_size)
        }

        self._initialize_camera()

        # Load Haarcascade for face detection
        # Ensure the path is correct or use a system path
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            self._log_error("Could not load face cascade classifier.")

    def _log_info(self, message):
        if self.logger: self.logger.log_info(f"VideoSensor: {message}")
        else: print(f"VideoSensor [INFO]: {message}")

    def _log_warning(self, message):
        if self.logger: self.logger.log_warning(f"VideoSensor: {message}")
        else: print(f"VideoSensor [WARN]: {message}")

    def _log_error(self, message):
        if self.logger: self.logger.log_error(f"VideoSensor: {message}")
        else: print(f"VideoSensor [ERROR]: {message}")

    def _initialize_camera(self):
        try:
            if self.camera_index is None:
                # Mock or testing mode, do not open actual camera
                return

            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self._log_warning(f"Could not open video camera {self.camera_index}.")
                self.cap = None
        except Exception as e:
            self._log_error(f"Error initializing camera: {e}")
            self.cap = None

    def get_frame(self):
        if self.cap is None or not self.cap.isOpened():
             # Try to reconnect occasionally?
             return None

        try:
            ret, frame = self.cap.read()
            if not ret:
                self._log_warning("Failed to capture video frame.")
                return None
            return frame
        except Exception as e:
             self._log_error(f"Error capturing frame: {e}")
             return None

    def calculate_activity(self, frame):
        """
        Calculates activity level for a given frame.
        """
        if frame is None:
            return 0.0

        try:
            # Convert to grayscale for simple diff
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Resize for performance
            gray = cv2.resize(gray, (100, 100))

            activity = 0.0
            if self.last_frame is not None:
                # Calculate absolute difference
                diff = cv2.absdiff(self.last_frame, gray)
                # Mean difference
                score = np.mean(diff)
                # Normalize (arbitrary scaling factor based on testing)
                activity = min(1.0, score / 50.0)

            self.last_frame = gray
            return activity
        except Exception as e:
            self._log_error(f"Error calculating activity: {e}")
            return 0.0

    def get_activity(self):
        """
        Calculates a simple 'activity level' based on pixel differences between frames.
        Returns a float 0.0 - 1.0 (normalized roughly).
        """
        frame = self.get_frame()
        if frame is None:
             return 0.0
        return self.calculate_activity(frame)

    def analyze_frame(self, frame):
        """
        Detects faces and estimates basic posture metrics.
        Returns a dict.
        """
        if frame is None:
            return {}

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            metrics = {
                "face_detected": len(faces) > 0,
                "face_count": len(faces),
                "face_locations": [], # List of [x, y, w, h]
                "face_size_ratio": 0.0, # Largest face width / image width
                "vertical_position": 0.0, # Center of face Y / image height
                "horizontal_position": 0.0 # Center of face X / image width
            }

            if len(faces) > 0:
                # Find largest face
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest_face

                # Convert all to list for JSON serialization
                metrics["face_locations"] = [list(f) for f in faces]

                img_h, img_w = frame.shape[:2]

                # Calculate raw metrics
                raw_size_ratio = float(w) / img_w
                raw_vert_pos = float(y + h/2) / img_h
                raw_horiz_pos = float(x + w/2) / img_w

                # Add to history
                self.history["face_size_ratio"].append(raw_size_ratio)
                self.history["vertical_position"].append(raw_vert_pos)
                self.history["horizontal_position"].append(raw_horiz_pos)

                # Return smoothed values
                metrics["face_size_ratio"] = float(np.mean(self.history["face_size_ratio"]))
                metrics["vertical_position"] = float(np.mean(self.history["vertical_position"]))
                metrics["horizontal_position"] = float(np.mean(self.history["horizontal_position"]))
            else:
                # If no face, we don't clear history immediately to avoid "glitches" if detection misses one frame.
                # But we return 0.0 for current metrics as per contract.
                # Optionally, we could return the last known smoothed value?
                # For now, adhering to contract: no face = 0.0, but maybe we should decay history?
                # Let's keep history for now, but return 0.0.
                pass

            return metrics
        except Exception as e:
            self._log_error(f"Error analyzing frame: {e}")
            return {}

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
