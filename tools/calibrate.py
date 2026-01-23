import time
import json
import os
import sys
import numpy as np
from typing import Dict, Any, List
import statistics

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.audio_sensor import AudioSensor
from sensors.video_sensor import VideoSensor
import config

class CalibrationEngine:
    def __init__(self):
        self.audio_sensor = AudioSensor()
        self.video_sensor = VideoSensor()
        self.user_data_dir = getattr(config, 'USER_DATA_DIR', 'user_data')
        self.config_path = os.path.join(self.user_data_dir, 'config.json')

        # Ensure user_data directory exists
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def load_current_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading existing config: {e}")
        return {}

    def save_config(self, new_config: Dict[str, Any]):
        current = self.load_current_config()
        current.update(new_config)
        with open(self.config_path, 'w') as f:
            json.dump(current, f, indent=4)
        print(f"Configuration saved to {self.config_path}")

    def calibrate_audio(self, duration: int = 10) -> Dict[str, float]:
        print(f"\n--- Audio Calibration ---")
        print("Instructions:")
        print("1. Keep the room in its 'normal' background state (fan on, ambient noise, etc).")
        print("2. Do not speak directly into the microphone.")
        print(f"3. Measuring for {duration} seconds...")
        print("Starting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Recording...")

        rms_values = []
        start_time = time.time()

        # Clear initial buffer
        self.audio_sensor.get_chunk()

        while time.time() - start_time < duration:
            chunk, err = self.audio_sensor.get_chunk()
            if chunk is not None and len(chunk) > 0:
                metrics = self.audio_sensor.analyze_chunk(chunk)
                rms = metrics.get('rms', 0.0)
                rms_values.append(rms)
                print(f"\rCurrent RMS: {rms:.4f}", end="", flush=True)
            elif err:
                print(f"\nWarning: Audio error: {err}")
            time.sleep(0.1)

        print("\nComplete.")

        if not rms_values:
            print("No audio data collected. Using defaults.")
            return {}

        mean_rms = statistics.mean(rms_values)
        max_rms = max(rms_values)
        std_dev = statistics.stdev(rms_values) if len(rms_values) > 1 else 0.0

        print(f"\nMean RMS: {mean_rms:.4f}")
        print(f"Max RMS: {max_rms:.4f}")
        print(f"Std Dev: {std_dev:.4f}")

        # 1. VAD Silence Threshold (Noise Floor)
        # Mean + 3 StdDevs, or Max + 20% margin
        vad_threshold = max(mean_rms + (3 * std_dev), max_rms * 1.2)
        vad_threshold = max(vad_threshold, 0.005) # Clamp min

        # 2. Audio High Threshold (Activity Trigger)
        # We want this to be higher than background noise, but sensitive enough to catch speech/loud sounds.
        # Mean + 6 StdDevs or Max * 2.0
        high_threshold = max(mean_rms + (6 * std_dev), max_rms * 2.0)
        high_threshold = max(high_threshold, 0.05) # Clamp min absolute
        high_threshold = min(high_threshold, 0.95) # Clamp max

        print(f"Suggested VAD Silence Threshold: {vad_threshold:.4f}")
        print(f"Suggested High Audio Threshold: {high_threshold:.4f}")

        return {
            "VAD_SILENCE_THRESHOLD": round(vad_threshold, 4),
            "AUDIO_THRESHOLD_HIGH": round(high_threshold, 4)
        }

    def calibrate_video(self, duration: int = 5) -> Dict[str, Any]:
        print(f"\n--- Video Calibration ---")
        print("Instructions:")
        print("1. Sit in your normal, neutral working posture.")
        print("2. Look at the screen naturally.")
        print(f"3. Measuring for {duration} seconds...")
        print("Starting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Capturing...")

        posture_samples = {
            "face_roll_angle": [],
            "face_size_ratio": [],
            "vertical_position": [],
            "horizontal_position": []
        }
        activity_samples = []

        start_time = time.time()
        frames_captured = 0

        while time.time() - start_time < duration:
            frame, err = self.video_sensor.get_frame()
            if frame is not None:
                metrics = self.video_sensor.process_frame(frame)

                # Activity (Raw)
                if "video_activity" in metrics:
                    activity_samples.append(metrics["video_activity"])

                # Posture
                if metrics.get("face_detected"):
                    posture_samples["face_roll_angle"].append(metrics.get("face_roll_angle", 0))
                    posture_samples["face_size_ratio"].append(metrics.get("face_size_ratio", 0))
                    posture_samples["vertical_position"].append(metrics.get("vertical_position", 0))
                    posture_samples["horizontal_position"].append(metrics.get("horizontal_position", 0))
                    frames_captured += 1
                    print(f"\rFace detected. Samples: {frames_captured}", end="", flush=True)
                else:
                    print("\rNo face detected (capturing activity only)...", end="", flush=True)
            elif err:
                 print(f"\nWarning: Video error: {err}")

            time.sleep(0.1)

        print("\nComplete.")

        results = {}

        # 1. Activity Threshold
        if activity_samples:
            v_mean = statistics.mean(activity_samples)
            v_std = statistics.stdev(activity_samples) if len(activity_samples) > 1 else 0.0
            v_max = max(activity_samples)

            # Threshold: Mean + 4*StdDev, or 1.5x Max. Floor of 5.0.
            rec_activity = max(v_mean + (4 * v_std), v_max * 1.5, 5.0)

            print(f"\nVideo Activity: Mean={v_mean:.2f}, Max={v_max:.2f}")
            print(f"Suggested Activity Threshold: {rec_activity:.2f}")
            results["VIDEO_ACTIVITY_THRESHOLD_HIGH"] = round(rec_activity, 2)
        else:
            print("\nNo video activity data collected.")

        # 2. Baseline Posture
        if frames_captured == 0:
            print("No valid face samples collected. Skipping posture calibration.")
        else:
            baseline = {
                "face_roll_angle": statistics.mean(posture_samples["face_roll_angle"]),
                "face_size_ratio": statistics.mean(posture_samples["face_size_ratio"]),
                "vertical_position": statistics.mean(posture_samples["vertical_position"]),
                "horizontal_position": statistics.mean(posture_samples["horizontal_position"])
            }

            print("Baseline Posture Calculated:")
            for k, v in baseline.items():
                print(f"  {k}: {v:.4f}")
            results["BASELINE_POSTURE"] = baseline

        return results

    def run(self):
        print("=== ASDGPT Calibration Wizard ===")

        try:
            input("Press Enter to start Audio Calibration (or Ctrl+C to quit)...")
            audio_results = self.calibrate_audio()

            input("\nPress Enter to start Video Calibration...")
            video_results = self.calibrate_video()

            print("\n--- Summary ---")
            new_config = {}
            new_config.update(audio_results)
            new_config.update(video_results)

            if new_config:
                print(json.dumps(new_config, indent=2))
                response = input("\nSave these settings to user_data/config.json? (y/n): ").strip().lower()
                if response == 'y':
                    self.save_config(new_config)
                    print("Settings saved.")
                else:
                    print("Discarded.")
            else:
                print("No changes to save.")

        except KeyboardInterrupt:
            print("\nCalibration cancelled.")
        finally:
            self.cleanup()

    def cleanup(self):
        print("Cleaning up sensors...")
        if self.audio_sensor:
            self.audio_sensor.release()
        if self.video_sensor:
            self.video_sensor.release()

if __name__ == "__main__":
    engine = CalibrationEngine()
    engine.run()
