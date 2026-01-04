#!/usr/bin/env python3
"""
Sensor Calibration Tool for ASDGPT
----------------------------------
This script runs a short calibration routine to measure ambient audio noise and
background video activity. It helps determine appropriate threshold values for
triggers in `config.py` and saves them to `user_data/calibration.json`.

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
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from sensors.audio_sensor import AudioSensor
    from sensors.video_sensor import VideoSensor
    import config
except ImportError as e:
    print(f"Error importing core modules: {e}")
    sys.exit(1)

# Ensure user_data directory exists
CALIBRATION_FILE = os.path.join(config.USER_DATA_DIR, "calibration.json")

def ensure_user_data_dir():
    if not os.path.exists(config.USER_DATA_DIR):
        os.makedirs(config.USER_DATA_DIR)

class ConsoleLogger:
    def log_info(self, msg): pass # Keep console clean
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")

def calibrate(duration=10):
    ensure_user_data_dir()
    print(f"\n--- Starting Sensor Calibration ({duration}s) ---")
    print("Please keep the environment in its 'resting' state.")
    print("- Keep background noise normal (don't speak).")
    print("- Don't move around excessively (sit normally).")

    # Initialize Sensors
    # Use 1.0s chunks for audio to get good RMS samples
    audio_sensor = AudioSensor(data_logger=ConsoleLogger(), chunk_duration=1.0)
    video_sensor = VideoSensor(camera_index=config.CAMERA_INDEX, data_logger=ConsoleLogger())

    if audio_sensor.has_error():
        print(f"[WARN] Audio sensor error: {audio_sensor.get_last_error()}")
    if video_sensor.cap is None or not video_sensor.cap.isOpened():
        print("[WARN] Video sensor error: Camera not found.")

    audio_levels = []
    video_activities = []

    # LogicEngine Activity Calculation Logic:
    # diff = cv2.absdiff(prev, curr); gray = cv2.cvtColor; mean = np.mean(gray)
    prev_frame = None

    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            # --- Audio ---
            if not audio_sensor.has_error():
                chunk, err = audio_sensor.get_chunk()
                if chunk is not None:
                    # LogicEngine uses: np.sqrt(np.mean(chunk**2)) which AudioSensor.analyze_chunk returns as 'rms'
                    metrics = audio_sensor.analyze_chunk(chunk)
                    rms = metrics.get("rms", 0.0)
                    audio_levels.append(rms)

            # --- Video ---
            # We replicate LogicEngine's exact calculation (Raw Mean Diff)
            # instead of using VideoSensor.calculate_activity (which normalizes).
            frame = video_sensor.get_frame()
            if frame is not None:
                if prev_frame is not None and frame.shape == prev_frame.shape:
                    diff = cv2.absdiff(prev_frame, frame)
                    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                    activity = np.mean(gray_diff)
                    video_activities.append(activity)

                prev_frame = frame.copy()

            # Progress bar
            elapsed = time.time() - start_time
            remaining = max(0, duration - elapsed)
            print(f"\rProgress: {elapsed:.1f}/{duration}s | Audio Samples: {len(audio_levels)} | Video Samples: {len(video_activities)}", end="")

            # Short sleep to not hammer CPU, but audio blocks for ~1s anyway
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nCalibration interrupted.")
    finally:
        audio_sensor.release()
        video_sensor.release()
        print()

    # --- Analysis & Stats ---
    results = {}

    print("\n--- Results ---")

    # Audio Analysis
    if audio_levels:
        a_mean = np.mean(audio_levels)
        a_std = np.std(audio_levels)
        a_max = np.max(audio_levels)
        # Threshold: Mean + 4*StdDev, ensuring it's above max seen
        rec_audio = max(a_mean + (4 * a_std), a_max * 1.2, 0.05)
        print(f"Audio RMS: Mean={a_mean:.4f}, Std={a_std:.4f}, Max={a_max:.4f}")
        print(f"Recommended Audio Threshold: {rec_audio:.4f}")
        results["AUDIO_THRESHOLD_HIGH"] = float(rec_audio)
    else:
        print("No audio data collected. Using default.")

    # Video Analysis
    if video_activities:
        v_mean = np.mean(video_activities)
        v_std = np.std(video_activities)
        v_max = np.max(video_activities)
        # Threshold: Mean + 4*StdDev, min 5.0
        rec_video = max(v_mean + (4 * v_std), v_max * 1.5, 5.0)
        print(f"Video Activity (Raw): Mean={v_mean:.2f}, Std={v_std:.2f}, Max={v_max:.2f}")
        print(f"Recommended Video Threshold: {rec_video:.2f}")
        results["VIDEO_ACTIVITY_THRESHOLD_HIGH"] = float(rec_video)
    else:
        print("No video data collected. Using default.")

    # Save to JSON
    if results:
        try:
            with open(CALIBRATION_FILE, 'w') as f:
                json.dump(results, f, indent=4)
            print(f"\n[SUCCESS] Calibration saved to: {CALIBRATION_FILE}")
            print("Restart the application for changes to take effect.")
        except Exception as e:
            print(f"\n[ERROR] Failed to save calibration file: {e}")
    else:
        print("\n[WARN] No calibration data generated.")

if __name__ == "__main__":
    calibrate()
