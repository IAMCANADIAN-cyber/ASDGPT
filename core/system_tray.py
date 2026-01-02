import pystray
from PIL import Image, ImageDraw # Pillow is needed for Image.open and potentially for creating icons on the fly
import threading
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
            "default": "assets/icons/default_icon.png"
        }
        self.icons = {name: load_image(path) for name, path in self.icon_paths.items()}

        self.current_icon_state = "default" # e.g., "active", "paused"

        # Menu items
        menu = (
            pystray.MenuItem('Pause/Resume', self.on_toggle_pause_resume),
            pystray.MenuItem('Snooze for 1 Hour', self.on_snooze),
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
            print(f"Tray icon updated to: {status}")
        else:
            self.current_icon_state = "default"
            if self.tray_icon:
                self.tray_icon.icon = self.icons["default"]
            print(f"Tray icon updated to default (unknown status: {status})")

    def update_tooltip(self, text: str):
        """Updates the tooltip (hover text) of the tray icon."""
        if self.tray_icon:
            self.tray_icon.title = text
            # Note: Depending on OS/implementation, title update might be instant or require icon refresh.
            # pystray usually handles it.

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

if __name__ == '__main__':
    # This is for testing the tray icon directly.
    # In the actual app, it will be instantiated and managed by main.py.
    print("Testing System Tray Icon...")

    # Mock application class
    class MockApp:
        def __init__(self):
            self.logic_engine = MockLogicEngine()
            self.intervention_engine = MockInterventionEngine()

        def on_pause_resume_pressed(self):
            print("MockApp: Pause/Resume toggled")
            if self.logic_engine.get_mode() == "paused":
                self.logic_engine.set_mode("active")
            else:
                self.logic_engine.set_mode("paused")
            tray.update_icon_status(self.logic_engine.get_mode())
            self.intervention_engine.notify_mode_change(self.logic_engine.get_mode())


        def quit_application(self):
            print("MockApp: Quitting application")
            tray.stop()
            # In a real app, you might need to exit the main loop or sys.exit()
            # For pystray, stopping the icon is often enough to allow the script to end if it's the only non-daemon thread.
            os._exit(0) # Force exit for the test script

    class MockLogicEngine:
        def __init__(self):
            self.mode = "active"
        def get_mode(self): return self.mode
        def set_mode(self, new_mode): self.mode = new_mode; print(f"MockLogic: Mode set to {new_mode}")

    class MockInterventionEngine:
        def notify_mode_change(self, mode): print(f"MockIntervention: Notified of mode {mode}")

    mock_app = MockApp()
    tray = ACRTrayIcon(mock_app)

    # Update status for testing
    tray.update_icon_status("active")

    print("Tray icon should be visible. Right-click for options. Close the tray or press Ctrl+C to exit if it hangs.")

    # pystray's run() is blocking, so it should be the last call or in a thread.
    # For this direct test, we run it on the main thread.
    tray.run_threaded()

    # Keep the main thread alive to see the tray icon, or pystray will run it.
    # If run_threaded() is used, the main thread can do other things or just wait.
    try:
        while True:
            time.sleep(1)
            # Example of how main app could interact:
            # if int(time.time()) % 10 == 0:
            #     print("Flashing icon from test loop")
            #     tray.flash_icon("error", original_status=mock_app.logic_engine.get_mode())

    except KeyboardInterrupt:
        print("Ctrl+C received, stopping tray icon.")
        tray.stop()
        mock_app.quit_application() # ensure clean exit
