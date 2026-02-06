from sensors.window_sensor import WindowSensor
import logging

logging.basicConfig(level=logging.INFO)

def test_window():
    print("Initializing WindowSensor...")
    ws = WindowSensor()
    print(f"Platform: {ws.platform}")
    print(f"Xprop available: {ws.xprop_available}")

    try:
        active = ws.get_active_window()
        print(f"Active Window: '{active}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_window()
