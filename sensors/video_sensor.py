import cv2
import time
import os
import numpy as np
import collections
import math
import threading
from typing import Optional, Callable, Dict, Any
import config

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

        self._lock = threading.RLock()

        # Error handling / Recovery state
        self.error_state = False
        self.last_error_message = ""
        self.retry_delay = 30  # seconds
        self.last_retry_time = 0

        # Eco Mode State
        self.last_face_detected_time = 0
        self.frame_count = 0

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

        # Load Haarcascade for eye detection
        self.eye_cascade = None
        try:
             eye_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_eye.xml')
             if os.path.exists(eye_cascade_path):
                 self.eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
                 if not self.eye_cascade.empty():
                     self._log_info(f"Loaded eye cascade from system path: {eye_cascade_path}")
                 else:
                     self._log_warning("Failed to load eye cascade (empty classifier).")
             else:
                 self._log_warning(f"Eye cascade not found at {eye_cascade_path}")
        except Exception as e:
            self._log_warning(f"Error loading eye cascade: {e}")

        if self.eye_cascade is None or self.eye_cascade.empty():
            self._log_warning("Head tilt estimation will be disabled.")

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
        with self._lock:
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

        with self._lock:
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
            gray_small = cv2.resize(gray, (100, 100))
            raw_score = self.calculate_raw_activity(gray_small)
            return min(1.0, raw_score / 50.0)

        except Exception as e:
            self._log_error(f"Error calculating activity: {e}")
            return 0.0

    def get_activity(self):
        """
        Convenience method to get frame and calculate activity.
        """
        frame, err = self.get_frame() # get_frame returns tuple
        return self.calculate_activity(frame)

    def calibrate(self, duration: float = 5.0, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, float]:
        """
        Captures video frames for a specified duration to calculate a baseline posture.
        Returns a dictionary of baseline metrics.
        """
        self._log_info(f"Starting video calibration for {duration}s...")

        posture_samples = {
            "face_roll_angle": [],
            "face_size_ratio": [],
            "vertical_position": [],
            "horizontal_position": []
        }

        start_time = time.time()
        frames_captured = 0

        while time.time() - start_time < duration:
            frame, err = self.get_frame()
            if frame is not None:
                metrics = self.process_frame(frame)
                if metrics.get("face_detected"):
                    for key in posture_samples:
                        posture_samples[key].append(metrics.get(key, 0))
                    frames_captured += 1
                    if progress_callback:
                        progress_callback(f"Face detected. Samples: {frames_captured}")
                else:
                    if progress_callback:
                        progress_callback("No face detected...")
            elif err:
                 self._log_warning(f"Calibration video error: {err}")

            time.sleep(0.1)

        if frames_captured == 0:
            self._log_warning("No valid face samples collected. Returning empty baseline.")
            return {}

        baseline = {
            "face_roll_angle": float(np.mean(posture_samples["face_roll_angle"])),
            "face_size_ratio": float(np.mean(posture_samples["face_size_ratio"])),
            "vertical_position": float(np.mean(posture_samples["vertical_position"])),
            "horizontal_position": float(np.mean(posture_samples["horizontal_position"]))
        }

        self._log_info(f"Baseline Posture Calculated: {baseline}")
        return baseline

    def _calculate_posture(self, metrics):
        """
        Calculates posture state based on face metrics.
        Uses config.BASELINE_POSTURE if available for relative comparison.
        """
        # Default to neutral if no face detected or calculation fails
        metrics["posture_state"] = "neutral"

        if not metrics.get("face_detected", False):
            return

        baseline = getattr(config, 'BASELINE_POSTURE', {})
        if not baseline:
            baseline = {}

        # Posture Heuristics

        # 1. Head Tilt
        current_roll = metrics.get("face_roll_angle", 0)
        baseline_roll = baseline.get("face_roll_angle", 0)

        if abs(current_roll - baseline_roll) > 20:
             if current_roll - baseline_roll > 0:
                 metrics["posture_state"] = "tilted_right"
             else:
                 metrics["posture_state"] = "tilted_left"

        # 2. Leaning Forward/Back
        elif baseline.get("face_size_ratio"):
             # Relative comparison
             current_size = metrics.get("face_size_ratio", 0)
             base_size = baseline["face_size_ratio"]
             if base_size > 0:
                 ratio = current_size / base_size
                 if ratio > 1.3:
                     metrics["posture_state"] = "leaning_forward"
                 elif ratio < 0.7:
                     metrics["posture_state"] = "leaning_back"
        # Fallback absolute thresholds for leaning
        elif metrics.get("face_size_ratio", 0) > 0.45:
            metrics["posture_state"] = "leaning_forward"
        elif metrics.get("face_size_ratio", 0) < 0.15:
            metrics["posture_state"] = "leaning_back"

        # 3. Slouching (Vertical Position)
        # Check if we already found a state, if so skip?
        # Original code was if/elif structure, so yes.
        if metrics["posture_state"] == "neutral":
            current_y = metrics.get("vertical_position", 0)
            baseline_y = baseline.get("vertical_position", 0.4) # Default approx center

            # Slouching = moving down (y increases)
            if current_y - baseline_y > 0.15:
                metrics["posture_state"] = "slouching"

    def _calculate_head_tilt(self, face_gray, face_w, face_h):
        """
        Estimates head tilt (roll) in degrees based on eye positions.
        Returns: float (degrees, positive = right tilt, negative = left tilt)
        """
        if self.eye_cascade is None or self.eye_cascade.empty():
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
            "face_roll_angle": 0.0,
            "posture_state": "neutral",
            "timestamp": time.time()
        }

        if frame is None:
            return metrics

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 1. Activity Calculation
            gray_small = cv2.resize(gray, (100, 100))
            raw_activity = self.calculate_raw_activity(gray_small)
            metrics["video_activity"] = float(raw_activity)
            metrics["normalized_activity"] = min(1.0, raw_activity / 50.0)

            # Smart Face Check (Eco Mode Logic)
            self.frame_count += 1
            should_detect_face = True

            # If activity is low, we might skip expensive face detection
            if metrics["video_activity"] <= config.VIDEO_WAKE_THRESHOLD:
                # But we check if we saw a face recently (grace period)
                time_since_face = time.time() - self.last_face_detected_time
                if time_since_face > 5.0:
                    # And we check strictly periodically (Heartbeat) to catch silent returns
                    # Assuming ~5Hz polling in idle, % 5 gives ~1Hz heartbeat
                    if self.frame_count % 5 != 0:
                        should_detect_face = False

            if should_detect_face:
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
                    self.last_face_detected_time = time.time()

                    # Find largest face
                    largest_face = max(faces, key=lambda f: f[2] * f[3])
                    x, y, w, h = largest_face

                    img_h, img_w = frame.shape[:2]

                    metrics["face_size_ratio"] = float(w) / img_w
                    metrics["vertical_position"] = float(y + h/2) / img_h
                    metrics["horizontal_position"] = float(x + w/2) / img_w

                    # Head Tilt Estimation (Face Roll)
                    face_roi_gray = gray[y:y+h, x:x+w]
                    metrics["face_roll_angle"] = self._calculate_head_tilt(face_roi_gray, w, h)

                    self._calculate_posture(metrics)

        except Exception as e:
            self._log_error(f"Error processing frame: {e}")

        return metrics

    def analyze_frame(self, frame):
        """
        Legacy wrapper for backward compatibility.
        """
        default_metrics = {
            "face_detected": False,
            "face_count": 0,
            "face_locations": [],
            "face_size_ratio": 0.0,
            "vertical_position": 0.0,
            "horizontal_position": 0.0
        }

        if frame is None:
            return default_metrics

        try:
            # We use process_frame to avoid duplicating logic
            metrics = self.process_frame(frame)
            return metrics
        except Exception as e:
            self._log_error(f"Error analyzing frame: {e}")
            return default_metrics

    def release(self):
        with self._lock:
            if self.cap:
                try:
                    self.cap.release()
                except Exception as e:
                    self._log_error(f"Error releasing video capture: {e}")
                finally:
                    self.cap = None
