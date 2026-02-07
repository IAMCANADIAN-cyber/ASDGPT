import os
import json
import time
import shutil
from typing import Optional, Dict, Any

class SocialMediaManager:
    """
    Manages social media content drafting.
    Generates captions via LMM (conceptually, or using LMMInterface) and saves drafts.
    """

    def __init__(self, lmm_interface=None, logger=None):
        self.lmm_interface = lmm_interface
        self.logger = logger
        self.drafts_dir = "drafts"

        if not os.path.exists(self.drafts_dir):
            os.makedirs(self.drafts_dir)

    def _log_info(self, msg: str) -> None:
        if self.logger:
            self.logger.log_info(f"SocialMediaManager: {msg}")
        else:
            print(f"SocialMediaManager: {msg}")

    def generate_caption(self, image_path: str, context: str = "") -> str:
        """
        Uses the LMM to generate a caption for the image.
        """
        if self.lmm_interface and os.path.exists(image_path):
            try:
                # Read image and encode to base64
                with open(image_path, "rb") as img_file:
                    import base64
                    b64_image = base64.b64encode(img_file.read()).decode('utf-8')

                # We can reuse process_data, but we need a way to ask a specific question.
                # LMMInterface is currently hardcoded for state estimation.
                # Ideally, we add a generic 'query' method to LMMInterface.
                # For now, we simulate a state estimation request but look for 'suggestion' or parse response?
                # Actually, adding a method to LMMInterface is cleaner.

                if hasattr(self.lmm_interface, 'generate_caption'):
                    return self.lmm_interface.generate_caption(b64_image, context)

            except Exception as e:
                self._log_info(f"LMM Caption generation failed: {e}")

        # Fallback
        base_caption = "Feeling myself."
        if "erotic" in context.lower():
            base_caption = "Late night vibes. 🌙 #mood"
        elif "workout" in context.lower():
            base_caption = "Grind never stops. 💪"

        return base_caption

    def create_draft(self, image_path: str, platform: str = "instagram", context: str = "") -> Optional[str]:
        """
        Creates a draft post (Image copy + Text file with caption).
        """
        if not os.path.exists(image_path):
            self._log_info(f"Image not found: {image_path}")
            return None

        try:
            timestamp = int(time.time())
            platform_dir = os.path.join(self.drafts_dir, platform)
            if not os.path.exists(platform_dir):
                os.makedirs(platform_dir)

            # Generate Caption
            caption = self.generate_caption(image_path, context)

            # Copy Image
            filename = os.path.basename(image_path)
            dest_image = os.path.join(platform_dir, f"{timestamp}_{filename}")
            shutil.copy2(image_path, dest_image)

            # Save Metadata/Caption
            meta_path = dest_image + ".json"
            meta_data = {
                "original_path": image_path,
                "timestamp": timestamp,
                "caption": caption,
                "platform": platform,
                "context": context
            }

            with open(meta_path, 'w') as f:
                json.dump(meta_data, f, indent=4)

            self._log_info(f"Draft created for {platform}: {dest_image}")
            return dest_image

        except Exception as e:
            self._log_info(f"Error creating draft: {e}")
            return None
