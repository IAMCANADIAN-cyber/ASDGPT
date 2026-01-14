import cv2
import time
import os
import numpy as np

class VideoSensor:
    def __init__(self, camera_index=0, data_logger=None):
        self.camera_index = camera_index
        self.logger = data_logger
        self.cap = None
        self.last_frame = None

        # Error handling / Recovery state
        self.error_state = False
        self.last_error_message = ""
        self.retry_delay = 30  # seconds
        self.last_retry_time = 0

        self._initialize_camera()

        # Load Haarcascade for face detection
        # Try local assets first, then system path
        cascade_filename = 'haarcascade_frontalface_default.xml'
        local_path = f"assets/haarcascades/{cascade_filename}"
        system_path = cv2.data.haarcascades + cascade_filename

        if os.path.exists(local_path):
             self.face_cascade = cv2.CascadeClassifier(local_path)
             if not self.face_cascade.empty():
                 self._log_info(f"Loaded face cascade from local assets: {local_path}")
             else:
                 self._log_warning(f"Failed to load local face cascade from {local_path}. Trying system path.")

        if not hasattr(self, 'face_cascade') or self.face_cascade.empty():
             self.face_cascade = cv2.CascadeClassifier(system_path)
             if self.face_cascade.empty():
                 self._log_error(f"Could not load face cascade classifier from {system_path}.")
             else:
                 self._log_info(f"Loaded face cascade from system path: {system_path}")

        # Load Eye Cascade for head tilt estimation
        eye_cascade_filename = 'haarcascade_eye.xml'
        system_eye_path = cv2.data.haarcascades + eye_cascade_filename
        self.eye_cascade = cv2.CascadeClassifier(system_eye_path)
        if self.eye_cascade.empty():
            self._log_warning(f"Could not load eye cascade from {system_eye_path}. Head tilt estimation will be disabled.")
        else:
            self._log_info(f"Loaded eye cascade from {system_eye_path}")

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

            self._log_info(f"Initializing video camera {self.camera_index}...")
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self._log_warning(f"Could not open video camera {self.camera_index}.")
                self.cap = None
                self.error_state = True
                self.last_error_message = "Camera failed to open."
            else:
                self._log_info("Video camera initialized successfully.")
                self.error_state = False
                self.last_error_message = ""

        except Exception as e:
            self._log_error(f"Error initializing camera: {e}")
            self.cap = None
            self.error_state = True
            self.last_error_message = str(e)

        self.last_retry_time = time.time()

    def get_frame(self):
        """
        Captures a frame from the video source.
        Returns: (frame, error_message)
            frame: numpy array or None
            error_message: str or None
        """
        # Attempt recovery if in error state
        if self.error_state:
            if time.time() - self.last_retry_time >= self.retry_delay:
                self._log_info("Attempting to re-initialize video camera...")
                self.release()
                self._initialize_camera()

            if self.error_state:
                return None, self.last_error_message

        if self.cap is None or not self.cap.isOpened():
             if not self.error_state:
                 self.error_state = True
                 self.last_error_message = "Camera not initialized or closed."
                 self.last_retry_time = time.time()
             return None, self.last_error_message

        try:
            ret, frame = self.cap.read()
            if not ret:
                self._log_warning("Failed to capture video frame (read returned False).")
                self.error_state = True
                self.last_error_message = "Failed to capture video frame."
                self.last_retry_time = time.time()
                return None, "Failed to capture video frame."

            # If we succeed, ensure error state is clear
            if self.error_state:
                self.error_state = False
                self.last_error_message = ""

            return frame, None
        except Exception as e:
             self._log_error(f"Error capturing frame: {e}")
             self.error_state = True
             self.last_error_message = str(e)
             self.last_retry_time = time.time()
             return None, str(e)

    def has_error(self):
        return self.error_state

    def get_last_error(self):
        return self.last_error_message

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
        frame = self.get_frame()
        return self.calculate_activity(frame)

    def _calculate_posture(self, metrics):
        """
        Calculates posture state based on face metrics.
        This is a heuristic estimation.
        """
        # Default to neutral if no face detected or calculation fails
        metrics["posture_state"] = "neutral"

        if not metrics.get("face_detected", False):
            return

        # Posture Heuristics
        # Note: These are simple 2D estimates and require calibration for accuracy.
        # Assumptions: Camera is roughly eye-level and centered.

        # Leaning Forward: Face becomes significantly larger
        # Thresholds should ideally be calibrated (e.g., normal ratio ~0.3-0.4)
        if metrics.get("face_size_ratio", 0) > 0.45:
            metrics["posture_state"] = "leaning_forward"
        # Leaning Back: Face becomes small
        elif metrics.get("face_size_ratio", 0) < 0.15:
            metrics["posture_state"] = "leaning_back"
        # Slouching: Face center moves down significantly
        # Assuming 0.0 is top, 1.0 is bottom. Normal eye level ~0.3-0.5
        elif metrics.get("vertical_position", 0) > 0.65:
            metrics["posture_state"] = "slouching"
        # Head Tilt (Roll): Significant angle
        elif abs(metrics.get("head_tilt", 0)) > 20:
             metrics["posture_state"] = "tilted"
        else:
            metrics["posture_state"] = "neutral"

    def _calculate_head_tilt(self, face_gray, face_w, face_h):
        """
        Estimates head tilt (roll) in degrees based on eye positions.
        Returns: float (degrees, positive = right tilt, negative = left tilt)
        """
        if self.eye_cascade.empty():
            return 0.0

        eyes = self.eye_cascade.detectMultiScale(face_gray)
        if len(eyes) != 2:
            return 0.0

        # Sort eyes by x-coordinate (left eye on screen is first)
        eyes = sorted(eyes, key=lambda e: e[0])
        (ex1, ey1, ew1, eh1) = eyes[0]
        (ex2, ey2, ew2, eh2) = eyes[1]

        # Centers
        p1 = (ex1 + ew1 // 2, ey1 + eh1 // 2)
        p2 = (ex2 + ew2 // 2, ey2 + eh2 // 2)

        # Delta
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        # Angle in degrees
        angle = np.degrees(np.arctan2(dy, dx))
        return angle

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

                # Head Tilt Estimation
                face_roi_gray = gray[y:y+h, x:x+w]
                metrics["head_tilt"] = self._calculate_head_tilt(face_roi_gray, w, h)

                self._calculate_posture(metrics)

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

                # Head Tilt Estimation
                face_roi_gray = gray[y:y+h, x:x+w]
                metrics["head_tilt"] = self._calculate_head_tilt(face_roi_gray, w, h)

                self._calculate_posture(metrics)

            return metrics
        except Exception as e:
            self._log_error(f"Error analyzing frame: {e}")
            return {}

    def release(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                self._log_error(f"Error releasing video capture: {e}")
            finally:
                self.cap = None
