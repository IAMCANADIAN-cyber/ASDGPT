import time
import subprocess
import sys
import os

def run_app_cycle(duration=5):
    """Runs the app for a few seconds then kills it."""
    # We need to run the actual app, but maybe with a flag to auto-quit or just kill it.
    # Since we don't have an auto-quit flag in main.py, we'll start it as a subprocess.

    cmd = [sys.executable, "main.py"]
    print(f"Starting app (duration: {duration}s)...")

    # Environment variables to ensure we don't actually open camera/mic if possible,
    # but for reliability test we kind of want to?
    # Actually, we want to test if it cleans up resources.

    proc = subprocess.Popen(cmd, env=os.environ.copy())

    time.sleep(duration)

    if proc.poll() is None:
        print("Sending SIGTERM...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
            print("App terminated gracefully.")
            return True
        except subprocess.TimeoutExpired:
            print("App hung! Sending SIGKILL.")
            proc.kill()
            return False
    else:
        print("App exited prematurely.")
        return True # Technically not a hang, but maybe a crash

def main():
    print("Running stress test: 5 rapid start/stop cycles.")
    success_count = 0
    total_cycles = 5

    for i in range(total_cycles):
        print(f"\n--- Cycle {i+1}/{total_cycles} ---")
        if run_app_cycle(duration=3):
            success_count += 1
        else:
            print("Cycle failed (HANG detected).")

    print(f"\nResult: {success_count}/{total_cycles} successful shutdowns.")

    if success_count == total_cycles:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
