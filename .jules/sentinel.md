# Sentinel: Graceful Shutdown Implementation

## What
Implemented `shutdown()` methods in `LogicEngine` and `InterventionEngine`, and wired them into `main.py`'s cleanup sequence. These methods use `thread.join(timeout=...)` to ensure background threads (LMM analysis, intervention sequences) are not abruptly killed when the application exits.

## Why
Previously, daemon threads were used without any cleanup logic. If the user quit the application while an LMM analysis was running or an intervention was active, the threads would be killed immediately. This could lead to:
- Loss of in-flight LMM data or state updates.
- Incomplete logging.
- Abrupt audio cut-off or partially executed intervention sequences.

## Verification
- Created `reproduce_shutdown_risk.py` which mocks a slow LMM call (2s sleep) and triggers shutdown.
- **Before Fix:** Script exited immediately, killing the mock LMM thread before it finished.
- **After Fix:** Script waits for the LMM thread to finish (printing "Analysis complete!") before exiting.
- **Existing Tests:** All passed (after fixing a missing `scipy` dependency).

## Risks
- **Shutdown Delay:** Shutdown now takes up to 5 seconds longer if an LMM call is active (timeout set to 5s).
- **Deadlock Potential:** If a thread refuses to join (e.g., stuck in C-level call without timeout), the `join(timeout=...)` prevents the app from hanging forever, so this risk is mitigated.

# Sentinel: Thread-Safe Sensor Release

## What
Added `threading.RLock` to `VideoSensor` and `AudioSensor` to protect critical sections (`get_frame`/`get_chunk` and `release`). Modified `main.py` shutdown sequence to join worker threads *before* releasing sensors.

## Why
A race condition existed where the main thread could call `sensor.release()` (setting internal capture objects to `None` or closing them) while a worker thread was inside `get_frame()` or `get_chunk()`. This could lead to `AttributeError` (if `None` check passed but object became `None` before read) or native crashes/undefined behavior in underlying libraries (OpenCV/PortAudio).

## Verification
- Created `tests/repro_crash.py` mocking the race condition (accessing object during release).
- Verified that without locks, the script failed/crashed.
- Verified that with locks, the shutdown was clean.
- Existing tests passed.

## Risks
- **Blocking I/O:** `get_chunk` (audio) and `get_frame` (video) hold the lock during blocking I/O. If `release()` is called, it waits for the current I/O operation to complete. For audio, this could delay shutdown by up to 1 chunk duration (default 1s). This is an acceptable trade-off for crash prevention.
