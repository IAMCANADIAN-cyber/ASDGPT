#!/usr/bin/env python3
"""
Sensor Calibration Tool for ASDGPT
----------------------------------
This script runs a short calibration routine to measure ambient audio noise and
background video activity. It helps determine appropriate threshold values for
triggers in `config.py`.

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
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from sensors.audio_sensor import AudioSensor
    from sensors.video_sensor import VideoSensor
    import config
except ImportError as e:
    print(f"Error importing core modules: {e}")
    print("Please run this script from the project root using: python tools/calibrate_sensors.py")
    sys.exit(1)


def calibrate_audio(duration=10):
    print(f"\n🎧 Calibrating Audio Sensor ({duration}s)...")
    print("Please remain silent and keep the environment in its 'normal' state.")

    # Use a dummy logger that prints to stdout
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
                pass # Retry logic is internal to sensor
            elif chunk is not None:
                metrics = sensor.analyze_chunk(chunk)
                rms_values.append(metrics["rms"])

                # Visual progress
                bar_len = int(metrics["rms"] * 100)
                print(f"\rRMS: {metrics['rms']:.4f} |{'=' * bar_len:<20}|", end="")

            # Small sleep to prevent busy loop, but consistent with chunk size
            # AudioSensor blocks on read, so this is just for safety
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
    p95_rms = np.percentile(rms_values, 95)

    print(f"\nAudio Calibration Results:")
    print(f"  Average RMS: {avg_rms:.4f}")
    print(f"  Max RMS:     {max_rms:.4f}")
    print(f"  95th %%ile:   {p95_rms:.4f}")

    # Recommendation: Threshold should be significantly above the 95th percentile of background noise
    # A multiplier of 1.5x to 2.0x is usually safe for "loud" detection
    recommended_threshold = max(0.05, p95_rms * 2.0)

    return recommended_threshold


def calibrate_video(duration=10):
    print(f"\n📷 Calibrating Video Sensor ({duration}s)...")
    print("Please ensure the camera is pointing at the user/background as normal.")

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

    try:
        while time.time() - start_time < duration:
            frame = sensor.get_frame()
            if frame is not None:
                activity = sensor.calculate_activity(frame)
                activity_values.append(activity)

                # Visual progress
                bar_len = int(activity * 20)
                print(f"\rActivity: {activity:.4f} |{'#' * bar_len:<20}|", end="")

            time.sleep(0.1)

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
    p95_act = np.percentile(activity_values, 95)

    print(f"\nVideo Calibration Results:")
    print(f"  Average Activity: {avg_act:.4f}")
    print(f"  Max Activity:     {max_act:.4f}")
    print(f"  95th %%ile:        {p95_act:.4f}")

    # Recommendation: Threshold above background movement (e.g., ceiling fan, lighting changes)
    recommended_threshold = max(0.1, p95_act * 1.5)

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

    env_vars = []

    if audio_rec is not None:
        print(f"Recommended AUDIO_THRESHOLD_HIGH: {audio_rec:.4f}")
        env_vars.append(f"AUDIO_THRESHOLD_HIGH={audio_rec:.4f}")
    else:
        print("Audio calibration failed or skipped.")

    if video_rec is not None:
        print(f"Recommended VIDEO_ACTIVITY_THRESHOLD_HIGH: {video_rec:.4f}")
        env_vars.append(f"VIDEO_ACTIVITY_THRESHOLD_HIGH={video_rec:.4f}")
    else:
        print("Video calibration failed or skipped.")

    print("\nTo apply these settings, add/update the following in your .env file:")
    print("--------------------------------------------------")
    for var in env_vars:
        print(var)
    print("--------------------------------------------------")
    print("Then restart the application.")

if __name__ == "__main__":
    main()
