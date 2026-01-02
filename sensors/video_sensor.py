import cv2
import time
import numpy as np

class VideoSensor:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.last_frame = None
        self._initialize_camera()

        # Load Haarcascade for face detection
        # Ensure the path is correct or use a system path
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            print("Error: Could not load face cascade classifier.")

    def _initialize_camera(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print(f"Warning: Could not open video camera {self.camera_index}.")
                self.cap = None
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.cap = None

    def get_frame(self):
        if self.cap is None or not self.cap.isOpened():
             # Try to reconnect occasionally?
             return None

        ret, frame = self.cap.read()
        if not ret:
            print("Warning: Failed to capture video frame.")
            return None

        return frame

    def calculate_activity(self, frame):
        """
        Calculates activity level for a given frame.
        """
        if frame is None:
            return 0.0

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

    def get_activity(self):
        """
        Calculates a simple 'activity level' based on pixel differences between frames.
        Returns a float 0.0 - 1.0 (normalized roughly).
        """
        frame = self.get_frame()
        return self.calculate_activity(frame)

    def analyze_frame(self, frame):
        """
        Detects faces and estimates basic posture metrics.
        Returns a dict.
        """
        if frame is None:
            return {}

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

            metrics["face_size_ratio"] = float(w) / img_w
            metrics["vertical_position"] = float(y + h/2) / img_h
            metrics["horizontal_position"] = float(x + w/2) / img_w

        return metrics

    def release(self):
        if self.cap:
            self.cap.release()
