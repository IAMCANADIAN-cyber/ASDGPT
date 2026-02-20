import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

class ImageProcessor:
    """
    Utilities for image manipulation, including Digital PTZ (Pan-Tilt-Zoom).
    """

    @staticmethod
    def crop_to_subject(frame: np.ndarray, face_metrics: Dict[str, Any], zoom_factor: float = 4.0) -> np.ndarray:
        """
        Crops the image to center on the detected face (or body approximation).
        Simulates PTZ camera behavior.

        Args:
            frame: The source video frame.
            face_metrics: Dictionary containing 'face_locations' or similar from VideoSensor.
            zoom_factor: Multiplier for face height to determine crop height.
                         Default 4.0 (Body/Bust shot).
                         2.0 would be a tight Headshot.

        Returns:
            Cropped (and potentially resized) image.
        """
        if frame is None:
            return None

        height, width = frame.shape[:2]

        # Default to center crop if no face
        center_x, center_y = width // 2, height // 2
        crop_w, crop_h = width, height

        face_locations = face_metrics.get("face_locations", [])
        if face_locations:
            # Assume first face or largest face
            largest_face = max(face_locations, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face

            center_x = x + w // 2
            center_y = y + h // 2

            # Determine crop size based on face size + margin
            target_h = int(h * zoom_factor)
            target_w = int(target_h * (width / height)) # Keep aspect ratio

            # Ensure we don't zoom IN more than resolution allows (digital zoom degrades)
            # Actually, we are cropping, so we ARE zooming in relative to full frame.
            # But we can't crop larger than the original frame.

            crop_h = min(height, target_h)
            crop_w = min(width, target_w)

        else:
            # No face? Maybe don't crop, or crop slightly to remove edges?
            # Just return full frame if no subject.
            return frame

        # Calculate coordinates
        x1 = max(0, center_x - crop_w // 2)
        y1 = max(0, center_y - crop_h // 2)
        x2 = min(width, x1 + crop_w)
        y2 = min(height, y1 + crop_h)

        # Adjust if we hit edges
        if x2 - x1 < crop_w:
            if x1 == 0: x2 = min(width, crop_w)
            else: x1 = max(0, width - crop_w)

        if y2 - y1 < crop_h:
            if y1 == 0: y2 = min(height, crop_h)
            else: y1 = max(0, height - crop_h)

        cropped = frame[y1:y2, x1:x2]
        return cropped
