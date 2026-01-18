#!/usr/bin/env python3
"""
Sensor Calibration Tool for ASDGPT
----------------------------------
This script runs a calibration routine to measure ambient audio noise and
background video activity. It generates personalized threshold values and
saves them to `user_data/calibration.json`.

Usage:
    python tools/calibrate_sensors.py [duration_in_seconds]

Dependencies:
    - numpy
    - sounddevice
    - opencv-python-headless
    - sensors.audio_sensor
    - sensors.video_sensor
"""

import time
import numpy as np
import os
import sys
import json
import threading
from typing import List, Optional

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sensors.audio_sensor import AudioSensor
    from sensors.video_sensor import VideoSensor
    import config
except ImportError as e:
    print(f"Error importing core modules: {e}")
    sys.exit(1)

# Mock DataLogger for standalone script
class ConsoleLogger:
    def log_info(self, msg): pass
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")

def calibrate(duration: int = 30):
    print(f"--- Starting Sensor Calibration ({duration}s) ---")
    print("Please keep the environment in its 'resting' state.")
    print("- Keep background noise normal (don't speak).")
    print("- Don't move around excessively (sit normally).")

    # Initialize Sensors
    audio_sensor = None
    video_sensor = None

    try:
        audio_sensor = AudioSensor(data_logger=ConsoleLogger(), chunk_duration=0.5)
        if audio_sensor.has_error():
            print(f"❌ Audio sensor init failed: {audio_sensor.get_last_error()}")
            audio_sensor = None
    except Exception as e:
        print(f"❌ Audio sensor exception: {e}")

    try:
        video_sensor = VideoSensor(camera_index=config.CAMERA_INDEX, data_logger=ConsoleLogger())
        # Warmup
        time.sleep(1) # Wait for camera to warm up
        if video_sensor.cap is None or not video_sensor.cap.isOpened():
            print(f"❌ Video sensor init failed (Index {config.CAMERA_INDEX}).")
            video_sensor = None
    except Exception as e:
        print(f"❌ Video sensor exception: {e}")

    if not audio_sensor and not video_sensor:
        print("No sensors available to calibrate.")
        return

    audio_samples = [] # RMS values
    video_samples = [] # Raw activity scores

    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            # Audio
            if audio_sensor:
                chunk, err = audio_sensor.get_chunk()
                if chunk is not None:
                    metrics = audio_sensor.analyze_chunk(chunk)
                    rms = metrics.get('rms', 0.0)
                    audio_samples.append(rms)

            # Video
            if video_sensor:
                # Use process_frame to get full metrics including activity
                metrics = video_sensor.process_frame(video_sensor.get_frame())
                if metrics:
                    # Use RAW activity (0-255 scale) because LogicEngine compares this against threshold
                    act = metrics.get('video_activity', 0.0)
                    video_samples.append(act)

            # Progress bar
            elapsed = time.time() - start_time
            print(f"\rMeasuring... {elapsed:.1f}/{duration}s | Audio: {len(audio_samples)} | Video: {len(video_samples)}", end="")

            # If audio sensor is missing, we need to sleep manually
            if not audio_sensor:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nCalibration interrupted.")
    finally:
        if audio_sensor: audio_sensor.release()
        if video_sensor: video_sensor.release()
        print()

    # --- Analysis & Recommendations ---
    results = {}

    # Audio Analysis
    if audio_samples:
        a_mean = np.mean(audio_samples)
        a_std = np.std(audio_samples)
        a_max = np.max(audio_samples)

        # Threshold: Mean + 4*StdDev, but at least 20% above Max to avoid random triggers
        rec_audio = max(a_mean + (4 * a_std), a_max * 1.2)
        # Enforce sanity floor (0.01) and ceiling (0.9)
        rec_audio = max(0.01, min(0.9, rec_audio))

        print(f"\n🎧 Audio (RMS): Mean={a_mean:.4f}, Max={a_max:.4f}, Std={a_std:.4f}")
        print(f"   -> Recommended Threshold: {rec_audio:.4f}")
        results["audio_threshold_high"] = rec_audio
    else:
        print("\n🎧 Audio: No data collected.")

    # Video Analysis
    if video_samples:
        v_mean = np.mean(video_samples)
        v_std = np.std(video_samples)
        v_max = np.max(video_samples)

        # Threshold: Mean + 4*StdDev, or 1.5x Max. Floor of 5.0.
        rec_video = max(v_mean + (4 * v_std), v_max * 1.5, 5.0)

        print(f"\n📷 Video (Raw Activity): Mean={v_mean:.2f}, Max={v_max:.2f}, Std={v_std:.2f}")
        print(f"   -> Recommended Threshold: {rec_video:.2f}")
        results["video_activity_threshold_high"] = rec_video
    else:
        print("\n📷 Video: No data collected.")

    # --- Save ---
    if results:
        # Save to user_data/calibration.json
        save_path = getattr(config, 'CALIBRATION_FILE', os.path.join("user_data", "calibration.json"))
        if not os.path.isabs(save_path) and "user_data" not in save_path:
             save_path = os.path.join("user_data", "calibration.json")

        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w') as f:
                json.dump(results, f, indent=4)
            print(f"\n✅ Calibration saved to: {save_path}")
            print("Restart the application for changes to take effect.")
        except Exception as e:
            print(f"\n❌ Failed to save calibration: {e}")

if __name__ == "__main__":
    dur = 10
    if len(sys.argv) > 1:
        try:
            dur = int(sys.argv[1])
        except:
            pass
    calibrate(dur)
