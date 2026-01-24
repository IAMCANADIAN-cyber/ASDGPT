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

# Sentinel: Resource Release on Crash

## What
Wrapped the main application loop in `main.py` within a `try...finally` block. Moved the `self._shutdown()` call into the `finally` block.

## Why
Previously, if an unhandled exception occurred within the `while self.running:` loop (e.g., in logic engine updates or queue processing), the loop would abort and the script would exit (via exception propagation) *without* calling `_shutdown()`. This meant that:
- Camera and Microphone handles might not be released properly.
- Background threads were not joined.
- `atexit` handlers were not reliable for this specific flow.

## Verification
- **Reproduction:** Created `tests/repro_shutdown_failure.py` which mocked the application and simulated a `RuntimeError` inside the main loop.
- **Before Fix:** Confirmed `_shutdown()` was NOT called.
- **After Fix:** Confirmed `_shutdown()` WAS called.
- **Cleanup:** Reproduction script was deleted after verification.

## Risks
- **Double Shutdown:** If `_shutdown` is called, and then `finally` block executes again (unlikely in this flow), `_shutdown` logic appears idempotent (checks for None/existence) so this is low risk.
- **Exception Masking:** The `try...finally` block does NOT catch the exception, so it still propagates to the top-level handler in `if __name__ == "__main__":`, preserving error logging behavior.
