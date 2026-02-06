
import sys
import os
import logging
from sensors.window_sensor import WindowSensor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WindowSensorVerifier")

def main():
    print("Initializing WindowSensor...")
    sensor = WindowSensor(logger=logger)

    print(f"OS Type: {sensor.os_type}")

    # Check for X11 vs Wayland
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    print(f"Session Type: {session_type}")

    # Check if xprop is installed
    import shutil
    if shutil.which("xprop"):
        print("xprop is installed.")
    else:
        print("xprop is NOT installed.")

    print("\nAttempting to get active window...")
    active_window = sensor.get_active_window()
    print(f"Active Window: '{active_window}'")

    if active_window == "Unknown":
        print("\nFAILURE: Could not detect active window.")
        sys.exit(1)
    else:
        print("\nSUCCESS: Detected active window.")
        sys.exit(0)

if __name__ == "__main__":
    main()
