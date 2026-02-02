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
<<<<<<< HEAD
=======

## 2026-01-29: Initialization Resource Leak

### Failure Mode
The `Application` class in `main.py` initialized sensors (`VideoSensor`, `AudioSensor`) sequentially in its `__init__` method. If a later sensor failed to initialize (raising an exception), the earlier sensors remained initialized (holding resources like camera handles) but the `Application` instance itself was never returned to the caller. Consequently, the `finally` block in `main` which calls `app.quit_application()` was skipped (because `app` was None), and the `VideoSensor.release()` method was never called. This left the camera device locked until the process was forcibly terminated or the OS cleaned it up.

### Fix
Wrapped the sensor initialization logic in `Application.__init__` within a `try...except` block. Initialize all sensor attributes to `None` first. In the `except` handler, explicitly check for and release any non-None sensors before re-raising the exception.

### Verification
Created a reproduction test `tests/test_init_reliability.py` that mocks `AudioSensor` to throw a `RuntimeError` and verifies that `VideoSensor.release()` is called in response.

### Learnings
- Constructors (`__init__`) that acquire external resources must be atomic or self-cleaning. If they fail, they must clean up partial state.
- Relying on `finally` blocks in the caller is insufficient if the constructor itself fails and returns nothing.
- Mocks for system libraries (`pystray`, `sounddevice`) are essential for testing reliability logic in headless CI environments.
>>>>>>> origin/merge-consolidation-feb-05-12320247635166828082
