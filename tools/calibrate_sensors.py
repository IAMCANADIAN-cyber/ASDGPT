#!/usr/bin/env python3
"""
Sensor Calibration Tool for ASDGPT
----------------------------------
Phase 1: Ambient Background
- Measures Audio RMS Noise Floor (for VAD)
- Measures Audio Peak Levels (for Loudness Triggers)
- Measures Video Activity (for Motion Triggers)

Phase 2: User Posture
- Measures Face Roll (for Head Tilt Baseline)
- Measures Vertical Position (for Slouching Baseline)

Saves results to `user_data/calibration.json`.
"""

import time
import json
import numpy as np
import os
import sys
import threading

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Handle headless environment (missing PortAudio)
try:
    import sounddevice
except OSError:
    import unittest.mock
    print("Warning: PortAudio not found. Mocking sounddevice for this run.")
    sys.modules['sounddevice'] = unittest.mock.MagicMock()

try:
    from sensors.audio_sensor import AudioSensor
    from sensors.video_sensor import VideoSensor
    import config
except ImportError as e:
    print(f"Error importing core modules: {e}")
    sys.exit(1)

# Mock Logger
class ConsoleLogger:
    def log_info(self, msg): pass
    def log_warning(self, msg): print(f"[WARN] {msg}")
    def log_error(self, msg, details=""): print(f"[ERROR] {msg} {details}")

def calibrate_ambient(audio_sensor, video_sensor, duration=10):
    print(f"\n--- Phase 1: Ambient Noise Calibration ({duration}s) ---")
    print("Instructions:")
    print("1. Keep the room in its 'normal' state (fans, AC, traffic noise).")
    print("2. Remain silent and relatively still.")
    print("3. Starting in 3 seconds...")
    time.sleep(3)

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
                # Discard return value, we assume internal state updates or we use get_frame
                # We need metrics
                frame, err = video_sensor.get_frame()
                metrics = video_sensor.process_frame(frame)
                if metrics:
                    act = metrics.get('video_activity', 0.0)
                    video_samples.append(act)

            # Progress bar
            elapsed = time.time() - start_time
            print(f"\rMeasuring... {elapsed:.1f}/{duration}s | Audio: {len(audio_samples)} | Video: {len(video_samples)}", end="")

            if not audio_sensor:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nInterrupted.")
        return {}, {}

    print("\nPhase 1 Complete.")

    results = {}

    # Audio Analysis
    if audio_samples:
        a_mean = np.mean(audio_samples)
        a_std = np.std(audio_samples)
        a_max = np.max(audio_samples)

        # 1. High Noise Trigger (Loudness)
        # Threshold: Mean + 4*StdDev, but at least 20% above Max to avoid random triggers
        rec_audio_high = max(a_mean + (4 * a_std), a_max * 1.2)
        rec_audio_high = max(0.01, min(0.9, rec_audio_high))
        results["audio_rms_threshold"] = rec_audio_high

        # 2. VAD Silence Floor
        # The floor of "silence" is the mean ambient noise.
        # We want VAD to trigger ABOVE this.
        # Recommended: Mean + 2*StdDev (covers 95% of noise).
        # We enforce a hard floor of 0.001 to avoid div/0 issues.
        rec_vad_silence = max(0.001, a_mean + (2 * a_std))
        results["vad_silence_threshold"] = rec_vad_silence

        print(f"\n🎧 Audio Stats:")
        print(f"   Mean RMS: {a_mean:.5f}, StdDev: {a_std:.5f}")
        print(f"   -> Recommended VAD Silence Threshold: {rec_vad_silence:.5f}")
        print(f"   -> Recommended High Trigger Threshold: {rec_audio_high:.4f}")
    else:
        print("   No audio data collected.")

    # Video Analysis
    if video_samples:
        v_mean = np.mean(video_samples)
        v_std = np.std(video_samples)
        v_max = np.max(video_samples)

        # High Activity Trigger
        rec_video_high = max(v_mean + (4 * v_std), v_max * 1.5, 5.0)
        results["video_activity_threshold"] = rec_video_high

        print(f"\n📷 Video Stats:")
        print(f"   Mean Activity: {v_mean:.2f}, StdDev: {v_std:.2f}")
        print(f"   -> Recommended Activity Threshold: {rec_video_high:.2f}")
    else:
        print("   No video data collected.")

    return results

def calibrate_posture(video_sensor, duration=10):
    print(f"\n--- Phase 2: Posture Calibration ({duration}s) ---")

    if not video_sensor:
        print("❌ Video sensor unavailable. Skipping posture calibration.")
        return {}

    print("Instructions:")
    print("1. SIT UP STRAIGHT in your 'ideal' working posture.")
    print("2. Look at the screen naturally.")
    print("3. Hold this position for the duration.")
    print("4. Starting in 5 seconds...")
    time.sleep(5)

    roll_samples = []
    vertical_samples = []

    start_time = time.time()
    try:
        while time.time() - start_time < duration:
            frame, err = video_sensor.get_frame()
            metrics = video_sensor.process_frame(frame)

            if metrics and metrics.get("face_detected"):
                roll = metrics.get("face_roll_angle", 0.0)
                vert = metrics.get("vertical_position", 0.0)

                roll_samples.append(roll)
                vertical_samples.append(vert)

            elapsed = time.time() - start_time
            print(f"\rMeasuring... {elapsed:.1f}/{duration}s | Valid Frames: {len(roll_samples)}", end="")
            # Video sensor runs at camera FPS, but process_frame is cpu bound.
            # We don't need to sleep much if get_frame is blocking/rate-limited.

    except KeyboardInterrupt:
        print("\nInterrupted.")
        return {}

    print("\nPhase 2 Complete.")

    results = {}

    if len(roll_samples) > 10:
        # Roll Analysis
        r_mean = np.mean(roll_samples)
        r_std = np.std(roll_samples)

        # Baseline is simply the mean angle (handles crooked camera)
        results["posture_roll_baseline"] = r_mean

        # Threshold is deviation allowed.
        # 3*Std captures 99% of "holding still" jitter.
        # But we want to allow some movement.
        # Let's say minimum 15 degrees, max 45.
        rec_roll_thresh = max(15.0, 4 * r_std)
        rec_roll_thresh = min(45.0, rec_roll_thresh)
        results["posture_roll_threshold"] = rec_roll_thresh

        # Vertical Analysis (Slouching)
        v_mean = np.mean(vertical_samples)
        v_std = np.std(vertical_samples)

        # Slouch threshold: Mean + Tolerance.
        # If I drop down, vertical position increases (0 is top).
        # Tolerance: usually 0.1 to 0.15 (10-15% of screen height drop)
        rec_slouch_thresh = v_mean + max(0.15, 4 * v_std)
        rec_slouch_thresh = min(0.95, rec_slouch_thresh) # Cap at bottom of screen
        results["posture_slouch_threshold"] = rec_slouch_thresh

        print(f"\n🧘 Posture Stats:")
        print(f"   Baseline Roll: {r_mean:.2f}° (Std: {r_std:.2f})")
        print(f"   Baseline Vertical: {v_mean:.2f} (Std: {v_std:.5f})")
        print(f"   -> Recommended Roll Baseline: {r_mean:.2f}")
        print(f"   -> Recommended Roll Threshold: {rec_roll_thresh:.2f}")
        print(f"   -> Recommended Slouch Threshold: {rec_slouch_thresh:.2f}")

    else:
        print("❌ Not enough valid face data collected. Is your face visible?")

    return results

def main():
    duration_ambient = 10
    duration_posture = 10

    if len(sys.argv) > 1:
        try:
            duration_ambient = int(sys.argv[1])
        except:
            pass

    # Initialize Sensors
    audio_sensor = None
    video_sensor = None

    try:
        audio_sensor = AudioSensor(data_logger=ConsoleLogger(), chunk_duration=0.5)
        if audio_sensor.has_error():
            print(f"Warning: Audio sensor init failed: {audio_sensor.get_last_error()}")
            audio_sensor = None
    except Exception as e:
        print(f"Warning: Audio sensor exception: {e}")

    try:
        video_sensor = VideoSensor(camera_index=config.CAMERA_INDEX, data_logger=ConsoleLogger())
        if video_sensor.cap is None or not video_sensor.cap.isOpened():
             print(f"Warning: Video sensor init failed.")
             video_sensor = None
    except Exception as e:
        print(f"Warning: Video sensor exception: {e}")

    if not audio_sensor and not video_sensor:
        print("No sensors available. Exiting.")
        sys.exit(1)

    # Run Phases
    res_ambient = calibrate_ambient(audio_sensor, video_sensor, duration=duration_ambient)

    # Prompt before phase 2
    if video_sensor:
        input("\nPress Enter to start Posture Calibration (Phase 2)...")
        res_posture = calibrate_posture(video_sensor, duration=duration_posture)
    else:
        res_posture = {}

    # Cleanup
    if audio_sensor: audio_sensor.release()
    if video_sensor: video_sensor.release()

    # Merge Results
    final_results = {**res_ambient, **res_posture}

    if not final_results:
        print("No calibration data generated.")
        return

    # Save
    save_path = config.CALIBRATION_FILE
    try:
        # Load existing to preserve other keys if any?
        # Actually, we probably want to overwrite these specific keys but keep others?
        # Current implementation assumes calibration.json is just for these.
        # But let's be safe.
        existing = {}
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r') as f:
                    existing = json.load(f)
            except:
                pass

        existing.update(final_results)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w') as f:
            json.dump(existing, f, indent=4)

        print(f"\n✅ Calibration successfully saved to: {save_path}")
        print("Please restart the application.")

    except Exception as e:
        print(f"\n❌ Failed to save calibration: {e}")

if __name__ == "__main__":
    main()
