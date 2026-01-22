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

    def calibrate_audio_limits(self, duration: int = 10) -> float:
        print(f"\n--- Audio High Limit Calibration ---")
        print("Please speak or create typical loud noise for your environment.")
        print("This sets the threshold for 'too loud' / overload.")
        print(f"Recording for {duration} seconds...")
        time.sleep(2)
        print("Go!")

        rms_values = []
        start_time = time.time()

        while time.time() - start_time < duration:
            chunk, err = self.audio_sensor.get_chunk()
            if chunk is not None and len(chunk) > 0:
                metrics = self.audio_sensor.analyze_chunk(chunk)
                rms = metrics.get('rms', 0.0)
                rms_values.append(rms)
                print(f"\rRMS: {rms:.4f}", end="", flush=True)
            time.sleep(0.1)

        print("\nComplete.")

        if not rms_values:
            return getattr(config, 'AUDIO_THRESHOLD_HIGH', 0.5)

        a_mean = statistics.mean(rms_values)
        a_std = statistics.stdev(rms_values) if len(rms_values) > 1 else 0.0
        a_max = max(rms_values)

        # Threshold: Mean + 4*StdDev, but at least 20% above Max
        rec_audio = max(a_mean + (4 * a_std), a_max * 1.2)
        rec_audio = max(0.01, min(0.9, rec_audio))

        print(f"Recommended Audio High Threshold: {rec_audio:.4f}")
        return rec_audio

    def calibrate_video_activity(self, duration: int = 10) -> float:
        print(f"\n--- Video Activity Limit Calibration ---")
        print("Please move normally/actively (e.g. typing, shifting).")
        print("This sets the threshold for 'high physical activity'.")
        print(f"Recording for {duration} seconds...")
        time.sleep(2)
        print("Go!")

        activity_values = []
        start_time = time.time()

        while time.time() - start_time < duration:
            frame, err = self.video_sensor.get_frame()
            if frame is not None:
                metrics = self.video_sensor.process_frame(frame)
                # Use raw activity (0-255)
                act = metrics.get('video_activity', 0.0)
                activity_values.append(act)
                print(f"\rActivity: {act:.2f}", end="", flush=True)
            time.sleep(0.1)

        print("\nComplete.")

        if not activity_values:
            return getattr(config, 'VIDEO_ACTIVITY_THRESHOLD_HIGH', 20.0)

        v_mean = statistics.mean(activity_values)
        v_std = statistics.stdev(activity_values) if len(activity_values) > 1 else 0.0
        v_max = max(activity_values)

        # Threshold: Mean + 4*StdDev, or 1.5x Max. Floor of 5.0.
        rec_video = max(v_mean + (4 * v_std), v_max * 1.5, 5.0)

        print(f"Recommended Video Activity Threshold: {rec_video:.2f}")
        return rec_video

    def calibrate_audio_silence(self, duration: int = 10) -> float:
        print(f"\n--- Audio Silence Calibration ---")
        print(f"Please remain silent for {duration} seconds...")
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
            print("No audio data collected. Using default.")
            return getattr(config, 'VAD_SILENCE_THRESHOLD', 0.01)

        mean_rms = statistics.mean(rms_values)
        max_rms = max(rms_values)
        std_dev = statistics.stdev(rms_values) if len(rms_values) > 1 else 0.0

        print(f"Mean RMS: {mean_rms:.4f}")
        print(f"Max RMS: {max_rms:.4f}")
        print(f"Std Dev: {std_dev:.4f}")

        # Calculate threshold: Mean + 3 StdDevs, or Max + 20% margin
        # We want to be safely above the noise floor
        suggested_threshold = max(mean_rms + (3 * std_dev), max_rms * 1.2)

        # Clamp to reasonable minimum
        suggested_threshold = max(suggested_threshold, 0.005)

        print(f"Suggested VAD Silence Threshold: {suggested_threshold:.4f}")
        return suggested_threshold

    def calibrate_video_posture(self, duration: int = 5) -> Dict[str, Any]:
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

        posture_samples = {
            "face_roll_angle": [],
            "face_size_ratio": [],
            "vertical_position": [],
            "horizontal_position": []
        }

        start_time = time.time()
        frames_captured = 0

        while time.time() - start_time < duration:
            frame, err = self.video_sensor.get_frame()
            if frame is not None:
                metrics = self.video_sensor.process_frame(frame)
                if metrics.get("face_detected"):
                    posture_samples["face_roll_angle"].append(metrics.get("face_roll_angle", 0))
                    posture_samples["face_size_ratio"].append(metrics.get("face_size_ratio", 0))
                    posture_samples["vertical_position"].append(metrics.get("vertical_position", 0))
                    posture_samples["horizontal_position"].append(metrics.get("horizontal_position", 0))
                    frames_captured += 1
                    print(f"\rFace detected. Samples: {frames_captured}", end="", flush=True)
                else:
                    print("\rNo face detected...", end="", flush=True)
            elif err:
                 print(f"\nWarning: Video error: {err}")

            time.sleep(0.1)

        print("\nComplete.")

        if frames_captured == 0:
            print("No valid face samples collected. Skipping posture calibration.")
            return {}

        baseline = {
            "face_roll_angle": statistics.mean(posture_samples["face_roll_angle"]),
            "face_size_ratio": statistics.mean(posture_samples["face_size_ratio"]),
            "vertical_position": statistics.mean(posture_samples["vertical_position"]),
            "horizontal_position": statistics.mean(posture_samples["horizontal_position"])
        }

        print("Baseline Posture Calculated:")
        for k, v in baseline.items():
            print(f"  {k}: {v:.4f}")

        return baseline

    def run(self):
        print("=== ASDGPT Calibration Wizard ===")

        try:
            print("\nStep 1: Audio Silence (Background Noise)")
            input("Press Enter to start...")
            silence_threshold = self.calibrate_audio_silence()

            print("\nStep 2: Audio Limits (Loudness)")
            input("Press Enter to start...")
            audio_high_threshold = self.calibrate_audio_limits()

            print("\nStep 3: Video Posture (Neutral)")
            input("Press Enter to start...")
            baseline_posture = self.calibrate_video_posture()

            print("\nStep 4: Video Activity (Movement)")
            input("Press Enter to start...")
            video_activity_threshold = self.calibrate_video_activity()

            print("\n--- Summary ---")
            new_config = {}

            if silence_threshold:
                new_config["VAD_SILENCE_THRESHOLD"] = round(silence_threshold, 4)
                print(f"VAD_SILENCE_THRESHOLD: {new_config['VAD_SILENCE_THRESHOLD']}")

            if audio_high_threshold:
                new_config["AUDIO_THRESHOLD_HIGH"] = round(audio_high_threshold, 4)
                print(f"AUDIO_THRESHOLD_HIGH: {new_config['AUDIO_THRESHOLD_HIGH']}")

            if baseline_posture:
                new_config["BASELINE_POSTURE"] = baseline_posture
                print(f"BASELINE_POSTURE: {json.dumps(baseline_posture, indent=2)}")

            if video_activity_threshold:
                new_config["VIDEO_ACTIVITY_THRESHOLD_HIGH"] = round(video_activity_threshold, 2)
                print(f"VIDEO_ACTIVITY_THRESHOLD_HIGH: {new_config['VIDEO_ACTIVITY_THRESHOLD_HIGH']}")

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
        if self.audio_sensor:
            self.audio_sensor.release()
        if self.video_sensor:
            self.video_sensor.release()

if __name__ == "__main__":
    engine = CalibrationEngine()
    engine.run()
