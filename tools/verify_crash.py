"""
verify_crash.py

Stress test script to verify system reliability during rapid start/stop cycles.
This mimics the 'Milestone 1' success metric.

It attempts to start the application (headless), let it run for a few seconds,
and then send a termination signal. It repeats this N times.

Success: The process exits with code 0 every time.
Failure: The process hangs, crashes (non-zero exit), or leaves zombie threads.
"""

import subprocess
import time
import sys
import os
import signal
import psutil

CYCLES = 5
RUN_DURATION_SEC = 3
GRACE_PERIOD_SEC = 3  # Time allowed for shutdown

def run_cycle(iteration):
    print(f"--- Cycle {iteration + 1}/{CYCLES} ---")

    cmd = [sys.executable, "main.py"]

    # Run in CWD = repo root
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd(),
        text=True
    )

    print(f"Started process PID: {process.pid}")

    # Let it run
    try:
        time.sleep(RUN_DURATION_SEC)
    except KeyboardInterrupt:
        pass

    # Check if it died early
    if process.poll() is not None:
        print(f"❌ Process died early with code {process.returncode}")
        print("STDOUT:", process.stdout.read())
        print("STDERR:", process.stderr.read())
        return False

    # Request graceful shutdown
    print("Sending SIGTERM...")
    process.terminate() # SIGTERM is cleaner than SIGINT for scripts usually, or SIGINT for KeyboardInterrupt simulation
    # main.py handles SIGINT and SIGTERM

    # Wait for exit
    try:
        stdout, stderr = process.communicate(timeout=GRACE_PERIOD_SEC)
        exit_code = process.returncode

        if exit_code == 0:
            print("✅ Shutdown clean (Exit Code 0)")
            return True
        else:
            print(f"❌ Shutdown failed (Exit Code {exit_code})")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return False

    except subprocess.TimeoutExpired:
        print("❌ Shutdown TIMED OUT (Hang detected)")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ Exception during cycle: {e}")
        process.kill()
        return False

def check_zombies():
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' and 'main.py' in (proc.info['cmdline'] or []) and proc.pid != current_pid:
                print(f"⚠️ Warning: Found lingering process {proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

if __name__ == "__main__":
    # Ensure we are in root
    if not os.path.exists("main.py"):
        print("Error: Run this from the repository root.")
        sys.exit(1)

    print(f"Starting {CYCLES} rapid start/stop cycles...")
    success_count = 0

    for i in range(CYCLES):
        if run_cycle(i):
            success_count += 1
        else:
            print("Aborting test due to failure.")
            break
        time.sleep(1)

    print(f"\nResults: {success_count}/{CYCLES} successful cycles.")

    if success_count == CYCLES:
        print("✅ Milestone 1 Verify Passed!")
        sys.exit(0)
    else:
        print("❌ Milestone 1 Verify Failed!")
        check_zombies()
        sys.exit(1)
