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
import time
import numpy as np
import os
import sys
import threading
from typing import List, Optional

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.audio_sensor import AudioSensor
from sensors.video_sensor import VideoSensor
import config

# Mock DataLogger for standalone script
class MockLogger:
    def log_info(self, msg): print(f"[INFO] {msg}")
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")

def calibrate(duration: int = 30):
    logger = MockLogger()
    print(f"--- Starting Sensor Calibration ({duration}s) ---")
    print("Please keep the environment in its 'resting' state.")
    print("- Keep background noise normal (don't speak).")
    print("- Don't move around excessively (sit normally).")

    # Initialize Sensors
    # Use higher sample rate/duration for better stats if needed, but defaults are fine.
    try:
        audio_sensor = AudioSensor(data_logger=logger, chunk_duration=1.0)
    except Exception as e:
        print(f"Failed to init audio sensor: {e}")
        audio_sensor = None

    try:
        # Camera index 0 is default
        video_sensor = VideoSensor(camera_index=config.CAMERA_INDEX, data_logger=logger)
    except Exception as e:
        print(f"Failed to init video sensor: {e}")
        video_sensor = None

    audio_levels: List[float] = []
    video_activities: List[float] = []

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
            # Audio
            if audio_sensor:
                chunk, error = audio_sensor.get_chunk()
                if chunk is not None:
                    # Calculate RMS locally or use sensor method if exposed?
                    # Sensor analyze_chunk returns dict.
                    metrics = audio_sensor.analyze_chunk(chunk)
                    rms = metrics.get('rms', 0.0)
                    audio_levels.append(rms)

            # Video
            if video_sensor:
                frame = video_sensor.get_frame()
                if frame is not None:
                    # Use calculate_activity which updates history
                    activity = video_sensor.calculate_activity(frame)
                    video_activities.append(activity)

            # Simple progress bar
            elapsed = time.time() - start_time
            print(f"\rProgress: {elapsed:.1f}/{duration}s | Audio Samples: {len(audio_levels)} | Video Samples: {len(video_activities)}", end="")

            # Sleep a bit to not hammer loop, but audio get_chunk is blocking for ~1s, so this loop is slow.
            # Video might be sampled less frequently if audio blocks.
            # Ideally we'd thread them, but for calibration, sequential 1s chunks is acceptable.
            # If audio blocks for 1s, video gets 1 fps. That's fine for "background activity".
            if not audio_sensor:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nCalibration cancelled.")
        return

    print("\n\n--- Analysis ---")

    # Audio Analysis
    rec_audio_threshold = 0.5 # Default fallback
    if audio_levels:
        a_mean = np.mean(audio_levels)
        a_std = np.std(audio_levels)
        a_max = np.max(audio_levels)

        # Suggestion: Mean + 4 * StdDev (covers 99.9% of normal background)
        # But ensure it's at least a bit above max seen.
        rec_audio_threshold = max(a_mean + (4 * a_std), a_max * 1.2, 0.05) # Minimum 0.05

        print(f"Audio RMS: Mean={a_mean:.4f}, Std={a_std:.4f}, Max={a_max:.4f}")
        print(f"Recommended High Audio Threshold: {rec_audio_threshold:.4f}")
    else:
        print("No audio data collected.")

    # Video Analysis
    rec_video_threshold = 20.0 # Default fallback
    if video_activities:
        v_mean = np.mean(video_activities)
        v_std = np.std(video_activities)
        v_max = np.max(video_activities)

        # Video activity is 0.0-1.0 in `calculate_activity`, but LogicEngine might expect 0-255 or similar?
        # LogicEngine: `diff = cv2.absdiff... self.video_activity = np.mean(gray_diff)`
        # Wait, `VideoSensor.calculate_activity` returns `score / 50.0`.
        # But `LogicEngine.process_video_data` does its OWN calculation: `np.mean(gray_diff)`.
        # This is a discrepancy!
        # LogicEngine uses `self.video_activity = np.mean(gray_diff)` (0-255).
        # VideoSensor.calculate_activity returns normalized 0-1.

        # WE MUST calibrate based on what LogicEngine uses.
        # LogicEngine duplicates the logic.
        # Let's fix LogicEngine to use VideoSensor's method or replicate LogicEngine's method here.
        # Since I can't easily change LogicEngine to use VideoSensor's method without verifying VideoSensor's method is what we want (it has memory),
        # I will replicate LogicEngine's raw mean diff logic here for calibration to match what LogicEngine sees.
        pass
    else:
        print("No video data collected.")

    # Re-evaluating Video Calibration based on LogicEngine implementation
    # LogicEngine: `np.mean(gray_diff)` where gray_diff is absdiff of two frames.
    # We need to simulate that.

    # Actually, `VideoSensor.calculate_activity` does: `score = np.mean(diff); return min(1.0, score / 50.0)`
    # So `score` is the same metric LogicEngine uses.
    # LogicEngine uses `video_activity_threshold_high = 20.0`.
    # 20.0 is on the scale of 0-255 (pixel intensity).
    # If VideoSensor returns `score/50.0`, then 1.0 = 50.0 pixel diff.

    # I should use the raw score to match LogicEngine's current 20.0 default.
    # VideoSensor.calculate_activity * 50.0 roughly recovers the raw score (clipped at 1.0/50).

    # Actually, let's just look at what I collected. `video_activities` from `calculate_activity` is normalized.
    # If I want to configure LogicEngine, I should probably standardise.
    # But for now, let's convert my collected `video_activities` back to raw scale approx
    # OR just assume LogicEngine should be updated to use the normalized score?
    # No, LogicEngine code I read uses `np.mean(gray_diff)` directly.
    # So `video_activity` in LogicEngine is 0-255.

    # My calibration script used `video_sensor.calculate_activity(frame)`.
    # This returns normalized 0-1.
    # I should probably just calculate the raw mean diff here to be safe and accurate to LogicEngine's behavior.

    # Redoing video calc in memory for stats if possible? No, data is gone.
    # I will rely on the fact that `video_activities` contains normalized data.
    # LogicEngine Threshold 20 => Normalized 0.4.

    if video_activities:
        # Convert back to raw scale (approx) for config if we stick to LogicEngine's current logic
        # But wait, `calculate_activity` clips at 1.0 (50.0 raw).
        # If motion exceeds 50.0, we lose data.
        # This is acceptable for "resting" state calibration.

        v_raw = [v * 50.0 for v in video_activities]
        v_mean = np.mean(v_raw)
        v_std = np.std(v_raw)
        v_max = np.max(v_raw)

        rec_video_threshold = max(v_mean + (4 * v_std), v_max * 1.5, 5.0) # Min 5.0

        print(f"Video Activity (Raw est): Mean={v_mean:.2f}, Std={v_std:.2f}, Max={v_max:.2f}")
        print(f"Recommended High Activity Threshold: {rec_video_threshold:.2f}")

    # Write to .env
    print("\n--- Updating Configuration ---")
    update = input(f"Update .env with Audio={rec_audio_threshold:.4f}, Video={rec_video_threshold:.2f}? (y/n): ")
    if update.lower() == 'y':
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

        # Read existing
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()

        # Update or Append
        new_lines = []
        keys_found = {'AUDIO': False, 'VIDEO': False}

        for line in lines:
            if line.startswith("AUDIO_THRESHOLD_HIGH="):
                new_lines.append(f"AUDIO_THRESHOLD_HIGH={rec_audio_threshold:.4f}\n")
                keys_found['AUDIO'] = True
            elif line.startswith("VIDEO_ACTIVITY_THRESHOLD_HIGH="):
                new_lines.append(f"VIDEO_ACTIVITY_THRESHOLD_HIGH={rec_video_threshold:.2f}\n")
                keys_found['VIDEO'] = True
            else:
                new_lines.append(line)

        if not keys_found['AUDIO']:
            new_lines.append(f"AUDIO_THRESHOLD_HIGH={rec_audio_threshold:.4f}\n")
        if not keys_found['VIDEO']:
            new_lines.append(f"VIDEO_ACTIVITY_THRESHOLD_HIGH={rec_video_threshold:.2f}\n")

        with open(env_path, 'w') as f:
            f.writelines(new_lines)

        print(f"Updated {env_path}")
    else:
        print("Skipped update.")

    # Clean up
    if audio_sensor: audio_sensor.release()
    if video_sensor: video_sensor.release()

if __name__ == "__main__":
    calibrate()
