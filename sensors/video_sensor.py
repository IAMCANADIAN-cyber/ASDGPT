import cv2
import time
import numpy as np

class VideoSensor:
    def __init__(self, camera_index=0, data_logger=None):
        self.camera_index = camera_index
        self.logger = data_logger
        self.cap = None
        self.last_frame = None
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

    def has_error(self):
        """Returns True if the sensor is in a persistent error state."""
        return self.cap is None or not self.cap.isOpened()

    def get_last_error(self):
        """Returns the last error message."""
        if self.cap is None:
            return "Camera not initialized."
        if not self.cap.isOpened():
            return "Camera connection lost."
        return ""

    def get_frame(self):
        """
        Captures a frame from the camera.
        Returns: (frame, error_message)
        """
        if self.cap is None or not self.cap.isOpened():
             # Try to reconnect occasionally? (Not implemented yet)
             return None, "Camera not connected"

        try:
            ret, frame = self.cap.read()
            if not ret:
                self._log_warning("Failed to capture video frame.")
                return None, "Failed to capture frame"
            return frame, None
        except Exception as e:
             self._log_error(f"Error capturing frame: {e}")
             return None, str(e)

    def calculate_raw_activity(self, gray_frame):
        """
        Calculates raw activity level (mean pixel difference) for a given grayscale frame.
        Updates self.last_frame.
        """
        if gray_frame is None:
            return 0.0

        activity = 0.0
        if self.last_frame is not None:
            # Ensure shapes match
            if self.last_frame.shape == gray_frame.shape:
                # Calculate absolute difference
                diff = cv2.absdiff(self.last_frame, gray_frame)
                # Mean difference
                activity = np.mean(diff)
            else:
                self._log_warning("Frame shape mismatch in activity calculation. Resetting last_frame.")

        self.last_frame = gray_frame
        return activity

    def calculate_activity(self, frame):
        """
        Calculates a simple 'activity level' based on pixel differences between frames.
        Returns a float 0.0 - 1.0 (normalized roughly).
        Wrapper around calculate_raw_activity for backward compatibility / normalized use.
        """
        if frame is None:
            return 0.0

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Resize for performance consistency if needed, but analyze_frame uses full size?
            # Let's keep it consistent. If we resize here, we should resize for everything.
            # LogicEngine used full size or didn't specify.
            # analyze_frame uses full size for face detection.
            # We'll use full size for now to be accurate, or small resize for speed.
            # Previous implementation resized to 100x100. Let's stick to that for 'activity' to match expected values.

            gray_small = cv2.resize(gray, (100, 100))

            raw_score = self.calculate_raw_activity(gray_small)

            # Normalize (arbitrary scaling factor based on testing)
            # Previous logic: min(1.0, score / 50.0)
            return min(1.0, raw_score / 50.0)

        except Exception as e:
            self._log_error(f"Error calculating activity: {e}")
            return 0.0

    def get_activity(self):
        """
        Convenience method to get frame and calculate activity.
        """
        frame, _ = self.get_frame()
        return self.calculate_activity(frame)

    def process_frame(self, frame):
        """
        Comprehensive frame processing:
        - Activity calculation (Raw and Normalized)
        - Face detection and metrics

        Returns a dictionary with all metrics.
        """
        metrics = {
            "video_activity": 0.0,      # Raw mean diff (0-255)
            "normalized_activity": 0.0, # Normalized (0.0-1.0)
            "face_detected": False,
            "face_count": 0,
            "face_locations": [],
            "face_size_ratio": 0.0,
            "vertical_position": 0.0,
            "horizontal_position": 0.0,
            "timestamp": time.time()
        }

        if frame is None:
            return metrics

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 1. Activity Calculation
            # We use a downscaled version for activity to match historical behavior/performance
            gray_small = cv2.resize(gray, (100, 100))

            raw_activity = self.calculate_raw_activity(gray_small)
            metrics["video_activity"] = float(raw_activity)
            metrics["normalized_activity"] = min(1.0, raw_activity / 50.0)

            # 2. Face Detection (using full size gray frame)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            metrics["face_detected"] = len(faces) > 0
            metrics["face_count"] = len(faces)
            metrics["face_locations"] = [list(f) for f in faces]

            if len(faces) > 0:
                # Find largest face
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest_face

                img_h, img_w = frame.shape[:2]

                metrics["face_size_ratio"] = float(w) / img_w
                metrics["vertical_position"] = float(y + h/2) / img_h
                metrics["horizontal_position"] = float(x + w/2) / img_w

        except Exception as e:
            self._log_error(f"Error processing frame: {e}")

        return metrics

    def analyze_frame(self, frame):
        """
        Legacy wrapper for backward compatibility if needed,
        or just for face detection specifically.
        """
        # We can implement this by calling process_frame and filtering keys,
        # but process_frame updates state (last_frame).
        # If analyze_frame is called separately, it might mess up activity diff if not careful.
        # But generally, LogicEngine should assume 'process_frame' is the main entry.
        # For now, we keep the original logic for analyze_frame to be safe,
        # BUT note that it doesn't touch 'last_frame'.

        if frame is None:
            return {}

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            metrics = {
                "face_detected": len(faces) > 0,
                "face_count": len(faces),
                "face_locations": [list(f) for f in faces],
                "face_size_ratio": 0.0,
                "vertical_position": 0.0,
                "horizontal_position": 0.0
            }

            if len(faces) > 0:
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest_face
                img_h, img_w = frame.shape[:2]
                metrics["face_size_ratio"] = float(w) / img_w
                metrics["vertical_position"] = float(y + h/2) / img_h
                metrics["horizontal_position"] = float(x + w/2) / img_w

            return metrics
        except Exception as e:
            self._log_error(f"Error analyzing frame: {e}")
            return {}

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
