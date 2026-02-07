import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

class ImageProcessor:
    """
    Utilities for image manipulation, including Digital PTZ (Pan-Tilt-Zoom).
    """

    @staticmethod
    def crop_to_subject(frame: np.ndarray, face_metrics: Dict[str, Any], zoom_factor: float = 1.5) -> np.ndarray:
        """
        Crops the image to center on the detected face (or body approximation).
        Simulates PTZ camera behavior.

        Args:
            frame: The source video frame.
            face_metrics: Dictionary containing 'face_locations' or similar from VideoSensor.
            zoom_factor: How tight to crop relative to face size.
                         Higher = wider view (zoom out), Lower = tighter (zoom in).
                         Wait, zoom_factor usually means magnification.
                         Let's define 'margin_factor':
                         1.0 = tight bounding box.
                         3.0 = rule of thirds / portrait.

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
            # Format usually (x, y, w, h) from OpenCV Haarcascade
            # But let's verify VideoSensor format. It is indeed (x, y, w, h).
            # VideoSensor uses: metrics["face_locations"] = [list(f) for f in faces]

            # Find largest face
            largest_face = max(face_locations, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face

            center_x = x + w // 2
            center_y = y + h // 2

            # Determine crop size based on face size + margin
            # We want a portrait-like crop if possible, or just centered.
            # Let's say we want the face to occupy ~1/3 of the frame height?
            # crop_h = h * 3
            # But we must respect aspect ratio if we want to save standard video?
            # Or just dynamic crop.

            # Let's aim for a crop that includes body (chest up)
            # Typically h * 4 for height
            target_h = int(h * 4.0)
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
