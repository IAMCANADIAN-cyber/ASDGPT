#!/usr/bin/env python3
"""
Sensor Calibration Tool for ASDGPT
----------------------------------
This script runs a calibration routine to measure ambient audio noise and
background video activity. It generates personalized threshold values and
saves them to `user_data/calibration.json` for the LogicEngine to use.

Usage:
    python tools/calibrate_sensors.py

Dependencies:
    - numpy
    - sounddevice
    - opencv-python-headless
    - sensors.audio_sensor
    - sensors.video_sensor
"""

import sys
import os
import time
import json
import numpy as np
import cv2

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from sensors.audio_sensor import AudioSensor
    from sensors.video_sensor import VideoSensor
    import config
except ImportError as e:
    print(f"Error importing core modules: {e}")
    print("Please run this script from the project root or tools/ directory.")
    sys.exit(1)


def calibrate_audio(duration=10):
    print(f"\n🎧 Calibrating Audio Sensor ({duration}s)...")
    print("Please remain silent and keep the environment in its 'normal' state.")

    # Use a dummy logger
    class ConsoleLogger:
        def log_info(self, msg): pass
        def log_warning(self, msg): print(f"[WARN] {msg}")
        def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")

    sensor = AudioSensor(data_logger=ConsoleLogger(), history_seconds=duration)

    if sensor.has_error():
        print(f"❌ Audio sensor initialization failed: {sensor.get_last_error()}")
        return None

    rms_values = []
    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            chunk, error = sensor.get_chunk()
            if error:
                pass
            elif chunk is not None:
                # LogicEngine uses: audio_level = np.sqrt(np.mean(chunk**2)) which is RMS
                # AudioSensor.analyze_chunk returns this as 'rms'
                metrics = sensor.analyze_chunk(chunk)
                rms = metrics.get("rms", 0.0)
                rms_values.append(rms)

                # Visual progress
                bar_len = int(rms * 100)
                print(f"\rRMS: {rms:.4f} |{'=' * bar_len:<20}|", end="")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nCalibration interrupted.")
    finally:
        sensor.release()
        print()

    if not rms_values:
        print("❌ No audio data collected.")
        return None

    avg_rms = np.mean(rms_values)
    max_rms = np.max(rms_values)
    # p95_rms = np.percentile(rms_values, 95)
    std_rms = np.std(rms_values)

    print(f"\nAudio Calibration Results:")
    print(f"  Average RMS: {avg_rms:.4f}")
    print(f"  Max RMS:     {max_rms:.4f}")
    print(f"  Std Dev:     {std_rms:.4f}")

    # Recommendation:
    # LogicEngine triggers if current_audio_level > AUDIO_THRESHOLD_HIGH
    # We want to avoid triggering on background noise.
    # Mean + 4*StdDev covers 99.99% of normal gaussian noise.
    recommended_threshold = max(0.01, avg_rms + (4 * std_rms), max_rms * 1.2)

    return recommended_threshold


def calibrate_video(duration=10):
    print(f"\n📷 Calibrating Video Sensor ({duration}s)...")
    print("Please ensure the camera is pointing at the user/background as normal.")
    print("Sit relatively still (normal working posture).")

    class ConsoleLogger:
        def log_info(self, msg): pass
        def log_warning(self, msg): print(f"[WARN] {msg}")
        def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")

    sensor = VideoSensor(camera_index=config.CAMERA_INDEX, data_logger=ConsoleLogger())

    # Warmup
    time.sleep(1)
    if sensor.cap is None or not sensor.cap.isOpened():
        print("❌ Video sensor initialization failed (Camera not found).")
        return None

    activity_values = []
    start_time = time.time()

    last_frame = None

    try:
        while time.time() - start_time < duration:
            frame = sensor.get_frame()
            if frame is not None:
                # Replicate LogicEngine's exact calculation:
                # diff = cv2.absdiff(prev, curr); gray_diff = cvtColor(diff, GRAY); mean(gray_diff)

                if last_frame is not None and frame.shape == last_frame.shape:
                    diff = cv2.absdiff(last_frame, frame)
                    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                    activity = np.mean(gray_diff)
                    activity_values.append(activity)

                    # Visual progress
                    bar_len = int(activity) # 0-255 scale
                    print(f"\rActivity: {activity:.2f} |{'#' * (bar_len // 5):<20}|", end="")

                last_frame = frame.copy()

            # Poll at roughly 10-15 FPS
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nCalibration interrupted.")
    finally:
        sensor.release()
        print()

    if not activity_values:
        print("❌ No video data collected.")
        return None

    avg_act = np.mean(activity_values)
    max_act = np.max(activity_values)
    std_act = np.std(activity_values)

    print(f"\nVideo Calibration Results (0-255 scale):")
    print(f"  Average Activity: {avg_act:.2f}")
    print(f"  Max Activity:     {max_act:.2f}")
    print(f"  Std Dev:          {std_act:.2f}")

    # Recommendation:
    # LogicEngine triggers if current_video_activity > VIDEO_ACTIVITY_THRESHOLD_HIGH
    # Default is 20.0.
    # We want a threshold that ignores minor shifting but catches "high activity".
    # Mean + 4*Std is a good baseline for "outlier" movement.
    # Ensure it's at least 5.0 to avoid noise triggers in pitch black/static.
    recommended_threshold = max(5.0, avg_act + (4 * std_act), max_act * 1.5)

    return recommended_threshold


def main():
    print("=========================================")
    print("      ASDGPT SENSOR CALIBRATION          ")
    print("=========================================")

    audio_rec = calibrate_audio()
    video_rec = calibrate_video()

    print("\n\n=========================================")
    print("       CALIBRATION SUMMARY               ")
    print("=========================================")

    calibration_data = {}

    if audio_rec is not None:
        print(f"Recommended AUDIO_THRESHOLD_HIGH: {audio_rec:.4f}")
        calibration_data["AUDIO_THRESHOLD_HIGH"] = float(f"{audio_rec:.4f}")
    else:
        print("Audio calibration failed or skipped.")

    if video_rec is not None:
        print(f"Recommended VIDEO_ACTIVITY_THRESHOLD_HIGH: {video_rec:.4f}")
        calibration_data["VIDEO_ACTIVITY_THRESHOLD_HIGH"] = float(f"{video_rec:.4f}")
    else:
        print("Video calibration failed or skipped.")

    if calibration_data:
        # Use config if available, else default
        save_path = getattr(config, 'CALIBRATION_FILE', "user_data/calibration.json")
        if not os.path.isabs(save_path) and "user_data" not in save_path:
             # Try to put it in user_data if path looks bare
             save_path = os.path.join("user_data", "calibration.json")

        # Force default location for safety if config attribute missing
        if not hasattr(config, 'CALIBRATION_FILE'):
             save_path = os.path.join("user_data", "calibration.json")

        print(f"\nSaving to {save_path}...")
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w') as f:
                json.dump(calibration_data, f, indent=4)
            print("✅ Calibration saved. Restart the application to apply.")
        except Exception as e:
            print(f"❌ Failed to save calibration: {e}")
    else:
        print("No data to save.")

if __name__ == "__main__":
    main()
