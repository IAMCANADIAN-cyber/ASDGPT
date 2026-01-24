import time
import json
import os
import sys
import numpy as np
from typing import Dict, Any, List

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

    def calibrate_audio_silence(self, duration: int = 10) -> float:
        print(f"\n--- Audio Silence Calibration (VAD) ---")
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

        mean_rms = np.mean(rms_values)
        max_rms = np.max(rms_values)
        std_dev = np.std(rms_values) if len(rms_values) > 1 else 0.0

        print(f"\nMean RMS: {mean_rms:.4f}")
        print(f"Max RMS: {max_rms:.4f}")
        print(f"Std Dev: {std_dev:.4f}")

        # Calculate threshold: Mean + 3 StdDevs, or Max + 20% margin
        # We want to be safely above the noise floor
        suggested_threshold = max(mean_rms + (3 * std_dev), max_rms * 1.2)

        # Clamp to reasonable minimum
        suggested_threshold = max(suggested_threshold, 0.005)

        print(f"Suggested VAD Silence Threshold: {suggested_threshold:.4f}")
        return float(suggested_threshold)

    def calibrate_activity_thresholds(self, duration: int = 10) -> Dict[str, float]:
        print(f"\n--- Activity Threshold Calibration (High Noise/Movement) ---")
        print("1. Keep the room in its 'normal' background state (fan on, ambient noise, etc).")
        print("2. Do not speak directly into the microphone.")
        print("3. Sit normally or keep the camera pointed at the usual background.")
        print(f"Measuring for {duration} seconds...")
        print("Starting in 3...")
        time.sleep(3)

        audio_samples = []
        video_samples = []
        start_time = time.time()

        while time.time() - start_time < duration:
            # Audio
            chunk, err = self.audio_sensor.get_chunk()
            if chunk is not None and len(chunk) > 0:
                metrics = self.audio_sensor.analyze_chunk(chunk)
                rms = metrics.get('rms', 0.0)
                audio_samples.append(rms)

            # Video
            frame, err = self.video_sensor.get_frame()
            if frame is not None:
                metrics = self.video_sensor.process_frame(frame)
                act = metrics.get('video_activity', 0.0)
                video_samples.append(act)

            # Progress
            elapsed = time.time() - start_time
            print(f"\rMeasuring... {elapsed:.1f}/{duration}s | Audio: {len(audio_samples)} | Video: {len(video_samples)}", end="", flush=True)
            time.sleep(0.1)

        print("\nComplete.")
        results = {}

        # Audio Analysis
        if audio_samples:
            a_mean = np.mean(audio_samples)
            a_std = np.std(audio_samples)
            a_max = np.max(audio_samples)

            # Threshold: Mean + 4*StdDev, but at least 20% above Max
            rec_audio = max(a_mean + (4 * a_std), a_max * 1.2)
            # Enforce sanity floor (0.01) and ceiling (0.9)
            rec_audio = max(0.01, min(0.9, rec_audio))

            print(f"\nAudio (RMS): Mean={a_mean:.4f}, Max={a_max:.4f}, Std={a_std:.4f}")
            print(f"Suggested AUDIO_THRESHOLD_HIGH: {rec_audio:.4f}")
            results["AUDIO_THRESHOLD_HIGH"] = float(rec_audio)
        else:
            print("Audio: No data collected.")

        # Video Analysis
        if video_samples:
            v_mean = np.mean(video_samples)
            v_std = np.std(video_samples)
            v_max = np.max(video_samples)

            # Threshold: Mean + 4*StdDev, or 1.5x Max. Floor of 5.0.
            rec_video = max(v_mean + (4 * v_std), v_max * 1.5, 5.0)

            print(f"Video (Activity): Mean={v_mean:.2f}, Max={v_max:.2f}, Std={v_std:.2f}")
            print(f"Suggested VIDEO_ACTIVITY_THRESHOLD_HIGH: {rec_video:.2f}")
            results["VIDEO_ACTIVITY_THRESHOLD_HIGH"] = float(rec_video)
        else:
            print("Video: No data collected.")

        return results

    def calibrate_video_posture(self, duration: int = 5) -> Dict[str, Any]:
        print(f"\n--- Video Posture Calibration (Baseline) ---")
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
            "face_roll_angle": float(np.mean(posture_samples["face_roll_angle"])),
            "face_size_ratio": float(np.mean(posture_samples["face_size_ratio"])),
            "vertical_position": float(np.mean(posture_samples["vertical_position"])),
            "horizontal_position": float(np.mean(posture_samples["horizontal_position"]))
        }

        print("Baseline Posture Calculated:")
        for k, v in baseline.items():
            print(f"  {k}: {v:.4f}")

        return baseline

    def run(self):
        print("=== ASDGPT Calibration Wizard ===")

        try:
            input("Press Enter to start Audio Calibration (or Ctrl+C to quit)...")
            silence_threshold = self.calibrate_audio_silence()

            input("\nPress Enter to start Activity Threshold Calibration (High Noise/Movement)...")
            activity_thresholds = self.calibrate_activity_thresholds()

            input("\nPress Enter to start Video Posture Calibration...")
            baseline_posture = self.calibrate_video_posture()

            print("\n--- Summary ---")
            new_config = {}
            if silence_threshold:
                new_config["VAD_SILENCE_THRESHOLD"] = round(silence_threshold, 4)
                print(f"VAD_SILENCE_THRESHOLD: {new_config['VAD_SILENCE_THRESHOLD']}")

            if activity_thresholds:
                new_config.update(activity_thresholds)
                for k, v in activity_thresholds.items():
                    print(f"{k}: {v}")

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
        if self.audio_sensor:
            self.audio_sensor.release()
        if self.video_sensor:
            self.video_sensor.release()

if __name__ == "__main__":
    engine = CalibrationEngine()
    engine.run()
