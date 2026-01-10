try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None
    print("Warning: pystray or PIL not found. System tray will be disabled.")
except Exception as e:
    # Catch Xlib/display errors during import
    pystray = None
    print(f"Warning: System tray disabled due to initialization error: {e}")

import threading
import time
import config
import os

# Helper function to load images, creating a fallback if not found
def load_image(path):
    if Image is None or ImageDraw is None:
        return None

    try:
        # Check if the path is absolute or relative and adjust
        if not os.path.isabs(path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(base_dir)
            icon_path = os.path.join(project_root, path)
        else:
            icon_path = path

        if not os.path.exists(icon_path):
            # Fallback: create a simple 64x64 image with Pillow
            img = Image.new('RGB', (64, 64), color='gray')
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), "N/A", fill='white')
            return img
        return Image.open(icon_path)
    except Exception as e:
        print(f"Error loading image {path}: {e}. Creating fallback.")
        img = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Err", fill='white')
        return img

class ACRTrayIcon:
    def __init__(self, application_instance):
        self.app = application_instance
        self.tray_icon = None
        self.thread = None
        self.current_icon_state = "default"

        if pystray is None:
            print("System Tray disabled (headless or missing dependencies).")
            return

        self.icon_paths = {
            "active": "assets/icons/active_icon.png",
            "paused": "assets/icons/paused_icon.png",
            "snoozed": "assets/icons/snoozed_icon.png",
            "error": "assets/icons/error_icon.png",
            "dnd": "assets/icons/dnd_icon.png",
            "default": "assets/icons/default_icon.png"
        }

        try:
            self.icons = {name: load_image(path) for name, path in self.icon_paths.items()}

            # Menu items
            menu = (
                pystray.MenuItem('Pause/Resume', self.on_toggle_pause_resume),
                pystray.MenuItem('Snooze for 1 Hour', self.on_snooze),
                pystray.MenuItem('Toggle DND', self.on_toggle_dnd),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Last: Helpful', self.on_feedback_helpful),
                pystray.MenuItem('Last: Unhelpful', self.on_feedback_unhelpful),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Quit', self.on_quit)
            )

            self.tray_icon = pystray.Icon(config.APP_NAME, self.icons[self.current_icon_state], config.APP_NAME, menu)

        except Exception as e:
            print(f"Failed to initialize System Tray Icon: {e}")
            self.tray_icon = None

    def run_threaded(self):
        if not self.tray_icon: return

        try:
            if not self.thread or not self.thread.is_alive():
                self.thread = threading.Thread(target=self.tray_icon.run, daemon=True)
                self.thread.start()
                print("System tray icon thread started.")
        except Exception as e:
            print(f"Error starting tray icon thread: {e}")

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        print("System tray icon stopped.")

    def on_toggle_pause_resume(self, icon, item):
        if self.app and hasattr(self.app, 'on_pause_resume_pressed'):
            self.app.on_pause_resume_pressed()

    def on_snooze(self, icon, item):
        if self.app and self.app.logic_engine:
            current_mode = self.app.logic_engine.get_mode()
            if current_mode != "snoozed":
                self.app.logic_engine.set_mode("snoozed")
                new_mode = self.app.logic_engine.get_mode()
                if hasattr(self.app, 'intervention_engine'):
                    self.app.intervention_engine.notify_mode_change(new_mode)
                self.update_icon_status(new_mode)

    def on_toggle_dnd(self, icon, item):
        if self.app and self.app.logic_engine:
            current_mode = self.app.logic_engine.get_mode()
            if current_mode == "dnd":
                self.app.logic_engine.set_mode("active")
            else:
                self.app.logic_engine.set_mode("dnd")

            new_mode = self.app.logic_engine.get_mode()
            if hasattr(self.app, 'intervention_engine'):
                self.app.intervention_engine.notify_mode_change(new_mode)
            self.update_icon_status(new_mode)

    def on_feedback_helpful(self, icon, item):
        if self.app and hasattr(self.app, 'on_feedback_helpful_pressed'):
            self.app.on_feedback_helpful_pressed()

    def on_feedback_unhelpful(self, icon, item):
        if self.app and hasattr(self.app, 'on_feedback_unhelpful_pressed'):
            self.app.on_feedback_unhelpful_pressed()

    def on_quit(self, icon, item):
        if self.app and hasattr(self.app, 'quit_application'):
            self.app.quit_application()
        self.stop()

    def update_icon_status(self, status):
        if not self.tray_icon: return

        if status in self.icons:
            self.current_icon_state = status
            self.tray_icon.icon = self.icons[status]
        else:
            self.current_icon_state = "default"
            self.tray_icon.icon = self.icons["default"]

    def update_tooltip(self, state_info):
        if not self.tray_icon: return

        tooltip_text = config.APP_NAME
        if self.current_icon_state == "dnd":
            tooltip_text = f"{config.APP_NAME} (DND)"
        elif isinstance(state_info, dict):
            arousal = state_info.get("arousal", "?")
            energy = state_info.get("energy", "?")
            focus = state_info.get("focus", "?")
            tooltip_text = f"{config.APP_NAME}\nA: {arousal} | E: {energy} | F: {focus}"
        elif isinstance(state_info, str):
            tooltip_text = f"{config.APP_NAME}\n{state_info}"

        self.tray_icon.title = tooltip_text

    def flash_icon(self, flash_status="active", original_status=None, duration=0.5, flashes=2):
        if not self.tray_icon: return
        if original_status is None: original_status = self.current_icon_state

        def _flash():
            for _ in range(flashes):
                self.update_icon_status(flash_status)
                time.sleep(duration / (2 * flashes))
                self.update_icon_status(original_status)
                time.sleep(duration / (2 * flashes))
            self.update_icon_status(original_status)

        flash_thread = threading.Thread(target=_flash, daemon=True)
        flash_thread.start()

    def notify_user(self, title, message):
        if self.tray_icon:
            try:
                self.tray_icon.notify(message, title)
            except Exception as e:
                print(f"Failed to send notification: {e}")

if __name__ == '__main__':
    print("Testing System Tray Icon (Hardened)...")
    class MockApp:
        def __init__(self): pass

    tray = ACRTrayIcon(MockApp())
    if tray.tray_icon:
        print("Tray initialized successfully.")
    else:
        print("Tray disabled (expected in headless env).")
