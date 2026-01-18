import pystray
from PIL import Image, ImageDraw # Pillow is needed for Image.open and potentially for creating icons on the fly
import threading
import time
import config
import os # For path joining

# Helper function to load images, creating a fallback if not found
def load_image(path):
    try:
        # Check if the path is absolute or relative and adjust
        if not os.path.isabs(path):
            # Assuming script is run from project root, or paths are relative to system_tray.py
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Construct path relative to the project root for assets
            # Project root is parent of 'core' directory
            project_root = os.path.dirname(base_dir)
            icon_path = os.path.join(project_root, path)
        else:
            icon_path = path

        if not os.path.exists(icon_path):
            print(f"Warning: Icon image not found at {icon_path}. Creating fallback.")
            # Fallback: create a simple 64x64 image with Pillow
            img = Image.new('RGB', (64, 64), color='gray')
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), "N/A", fill='white')
            return img
        return Image.open(icon_path)
    except Exception as e:
        print(f"Error loading image {path}: {e}. Creating fallback.")
        # Fallback: create a simple 64x64 image with Pillow
        img = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Err", fill='white')
        return img

class ACRTrayIcon:
    def __init__(self, application_instance):
        self.app = application_instance # Reference to the main Application instance
        self.icon_paths = {
            "active": "assets/icons/active_icon.png",
            "paused": "assets/icons/paused_icon.png",
            "snoozed": "assets/icons/snoozed_icon.png",
            "error": "assets/icons/error_icon.png",
            "dnd": "assets/icons/dnd_icon.png",
            "default": "assets/icons/default_icon.png"
        }
        self.icons = {name: load_image(path) for name, path in self.icon_paths.items()}

        self.current_icon_state = "default" # e.g., "active", "paused"

        # Calculate snooze label
        snooze_minutes = config.SNOOZE_DURATION // 60
        if snooze_minutes == 60:
            snooze_label = 'Snooze for 1 Hour'
        elif snooze_minutes > 60 and snooze_minutes % 60 == 0:
            snooze_label = f'Snooze for {snooze_minutes // 60} Hours'
        else:
            snooze_label = f'Snooze for {snooze_minutes} Minutes'

        # Menu items
        menu = (
            pystray.MenuItem('Pause/Resume', self.on_toggle_pause_resume),
            pystray.MenuItem(snooze_label, self.on_snooze),
            pystray.MenuItem('Toggle DND', self.on_toggle_dnd),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Last: Helpful', self.on_feedback_helpful),
            pystray.MenuItem('Last: Unhelpful', self.on_feedback_unhelpful),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self.on_quit)
        )

        self.tray_icon = pystray.Icon(config.APP_NAME, self.icons[self.current_icon_state], config.APP_NAME, menu)
        self.thread = None

    def run_threaded(self):
        # pystray needs to run in its own thread if the main app has its own loop
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.thread.start()
            print("System tray icon thread started.")

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2) # Wait for thread to finish
        print("System tray icon stopped.")

    def on_toggle_pause_resume(self, icon, item):
        print("Tray: Pause/Resume clicked")
        if self.app and hasattr(self.app, 'on_pause_resume_pressed'):
            self.app.on_pause_resume_pressed() # Call the main app's handler

    def on_snooze(self, icon, item):
        print("Tray: Snooze clicked")
        if self.app and self.app.logic_engine:
            current_mode = self.app.logic_engine.get_mode()
            if current_mode != "snoozed":
                self.app.logic_engine.set_mode("snoozed") # Directly set to snoozed
                new_mode = self.app.logic_engine.get_mode()
                print(f"Mode changed to {new_mode} via tray snooze.")
                if hasattr(self.app, 'intervention_engine'):
                    self.app.intervention_engine.notify_mode_change(new_mode)
                self.update_icon_status(new_mode) # Update icon immediately
            else: # Already snoozing, maybe unsnooze it? Or just ignore. For now, ignore.
                print("Already snoozing.")

    def on_toggle_dnd(self, icon, item):
        print("Tray: Toggle DND clicked")
        if self.app and self.app.logic_engine:
            current_mode = self.app.logic_engine.get_mode()
            if current_mode == "dnd":
                # Toggle OFF -> Active
                self.app.logic_engine.set_mode("active")
            else:
                # Toggle ON -> DND
                self.app.logic_engine.set_mode("dnd")

            new_mode = self.app.logic_engine.get_mode()
            print(f"Mode changed to {new_mode} via tray DND toggle.")
            if hasattr(self.app, 'intervention_engine'):
                self.app.intervention_engine.notify_mode_change(new_mode)
            self.update_icon_status(new_mode)

    def on_feedback_helpful(self, icon, item):
        print("Tray: Feedback 'Helpful' clicked")
        if self.app and hasattr(self.app, 'on_feedback_helpful_pressed'):
            self.app.on_feedback_helpful_pressed()

    def on_feedback_unhelpful(self, icon, item):
        print("Tray: Feedback 'Unhelpful' clicked")
        if self.app and hasattr(self.app, 'on_feedback_unhelpful_pressed'):
            self.app.on_feedback_unhelpful_pressed()

    def on_quit(self, icon, item):
        print("Tray: Quit clicked")
        if self.app and hasattr(self.app, 'quit_application'):
            self.app.quit_application()
        self.stop()

    def update_icon_status(self, status):
        """
        Updates the tray icon based on the application status.
        :param status: A string like "active", "paused", "snoozed", "error".
        """
        if status in self.icons:
            self.current_icon_state = status
            if self.tray_icon:
                self.tray_icon.icon = self.icons[status]
            # Logging handled by caller or kept minimal to avoid spam
        else:
            self.current_icon_state = "default"
            if self.tray_icon:
                self.tray_icon.icon = self.icons["default"]
            print(f"Tray icon updated to default (unknown status: {status})")

    def update_tooltip(self, state_info):
        """
        Updates the tooltip with the provided state information.
        :param state_info: A dictionary or string containing state details.
        """
        if not self.tray_icon:
            return

        tooltip_text = config.APP_NAME # Default

        if self.current_icon_state == "dnd":
            tooltip_text = f"{config.APP_NAME} (DND)"
        elif isinstance(state_info, dict):
            if not state_info:
                tooltip_text = f"{config.APP_NAME}\nInitializing..."
            else:
                # Format: "A: 50 | E: 80 | F: 50" (Shortened for tooltip)
                # We try to fit all 5 dimensions if available
                # A=Arousal, O=Overload, F=Focus, E=Energy, M=Mood

                parts = []

                # Line 1: Arousal, Overload, Focus
                line1 = []
                line1.append(f"A: {state_info.get('arousal', '?')}")
                line1.append(f"O: {state_info.get('overload', '?')}")
                line1.append(f"F: {state_info.get('focus', '?')}")

                # Line 2: Energy, Mood
                line2 = []
                line2.append(f"E: {state_info.get('energy', '?')}")
                line2.append(f"M: {state_info.get('mood', '?')}")

                if line1: parts.append(" ".join(line1))
                if line2: parts.append(" ".join(line2))

                if parts:
                    tooltip_text = f"{config.APP_NAME}\n" + "\n".join(parts)
                else:
                     tooltip_text = f"{config.APP_NAME}\nNo State Data"
        elif isinstance(state_info, str):
            tooltip_text = f"{config.APP_NAME}\n{state_info}"

        self.tray_icon.title = tooltip_text

    def flash_icon(self, flash_status="active", original_status=None, duration=0.5, flashes=2):
        """Briefly changes the icon to indicate an event (e.g., intervention)."""
        if not self.tray_icon: return

        if original_status is None:
            original_status = self.current_icon_state

        def _flash():
            for _ in range(flashes):
                self.update_icon_status(flash_status)
                time.sleep(duration / (2 * flashes))
                self.update_icon_status(original_status)
                time.sleep(duration / (2 * flashes))
            # Ensure it returns to the correct state
            self.update_icon_status(original_status)

        # Run flash in a separate thread to not block
        flash_thread = threading.Thread(target=_flash, daemon=True)
        flash_thread.start()

    def notify_user(self, title, message):
        """
        Sends a system notification.
        :param title: The title of the notification.
        :param message: The body of the notification.
        """
        if self.tray_icon:
            try:
                self.tray_icon.notify(message, title)
                print(f"Notification sent: {title} - {message}")
            except Exception as e:
                print(f"Failed to send notification: {e}")
