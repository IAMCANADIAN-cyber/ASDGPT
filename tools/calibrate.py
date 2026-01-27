import time
import json
import os
import sys
import numpy as np
from typing import Dict, Any, List, Optional
import statistics

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Replaces legacy tools/calibrate_sensors.py
# This wizard calibrates VAD (Silence) and Posture (Neutral State)
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

    def calibrate_audio_silence(self, duration: int = 30) -> float:
        print(f"\n--- Audio Silence Calibration ---")
        print(f"Please remain silent for {duration} seconds...")
        print("Starting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Recording...")

        def progress_callback(rms):
            print(f"\rCurrent RMS: {rms:.4f}", end="", flush=True)

        try:
            suggested_threshold = self.audio_sensor.calibrate(duration=float(duration), progress_callback=progress_callback)
            print("\nComplete.")
            return suggested_threshold
        except KeyboardInterrupt:
            print("\nAudio calibration interrupted by user.")
            return getattr(config, 'VAD_SILENCE_THRESHOLD', 0.01)
        except Exception as e:
            print(f"\nError during calibration: {e}")
            return getattr(config, 'VAD_SILENCE_THRESHOLD', 0.01)

    def calibrate_video_posture(self, duration: int = 30) -> Dict[str, Any]:
        print(f"\n--- Video Posture Calibration ---")
        print("Please sit in your normal, neutral working posture.")
        print("Look at the screen naturally.")
        print(f"Hold this position for {duration} seconds...")
        print("Starting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Capturing...")

        def progress_callback(msg):
            print(f"\r{msg}", end="", flush=True)

        try:
            baseline = self.video_sensor.calibrate(duration=float(duration), progress_callback=progress_callback)
            print("\nComplete.")

            if not baseline:
                print("No valid face samples collected. Skipping posture calibration.")
                return {}

            print("Baseline Posture Calculated:")
            for k, v in baseline.items():
                print(f"  {k}: {v:.4f}")

            return baseline
        except KeyboardInterrupt:
            print("\nVideo calibration interrupted by user.")
            return {}
        except Exception as e:
            print(f"\nError during video calibration: {e}")
            return {}

    def run(self):
        print("=== ASDGPT Calibration Wizard ===")

        try:
            input("Press Enter to start Audio Calibration (or Ctrl+C to quit)...")
            silence_threshold = self.calibrate_audio_silence()

            input("\nPress Enter to start Video Calibration...")
            baseline_posture = self.calibrate_video_posture()

            print("\n--- Summary ---")
            new_config = {}
            if silence_threshold:
                new_config["VAD_SILENCE_THRESHOLD"] = round(silence_threshold, 4)
                print(f"VAD_SILENCE_THRESHOLD: {new_config['VAD_SILENCE_THRESHOLD']}")

            if baseline_posture:
                new_config["BASELINE_POSTURE"] = baseline_posture
                print(f"BASELINE_POSTURE: {json.dumps(baseline_posture, indent=2)}")

            if new_config:
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
        if hasattr(self, 'audio_sensor') and self.audio_sensor:
            self.audio_sensor.release()
        if hasattr(self, 'video_sensor') and self.video_sensor:
            self.video_sensor.release()

if __name__ == "__main__":
    engine = CalibrationEngine()
    engine.run()
