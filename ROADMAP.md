# ASDGPT Weekly Roadmap Refresh

**Date:** 2024-06-05
**Status:** STABLE

## 🗺️ Executive Summary
The system has reached a stable "v0.5" state. The core loops (Audio/Video -> Logic -> Intervention) are functional, and the critical "Crash/Zombie Thread" issues have been resolved. The `ReplayHarness` now allows for rapid, noise-free logic testing. The next 7 days are focused on **Signal Fidelity** (making sure the sensors don't lie) and **Filling Gaps** (implementing the missing Biometric sensor and hardening the LMM connection).

## 1. Change Summary (Last 7 Days)
*   **Merged**:
    *   `navigator-context-persistence-loop` (PR #70): Established user feedback loop (Helpful/Unhelpful).
    *   Reliability Fixes: `verify_crash.py` confirms 10/10 clean shutdowns (no zombie threads).
*   **Completed**:
    *   **Replay Harness**: `tools/replay_harness.py` is live.
    *   **VAD v1**: `AudioSensor` now has `is_speech` logic based on Pitch/ZCR.
    *   **DND Mode**: Tray icon supports DND, and `LogicEngine` respects it.
*   **Gaps Identified**:
    *   `sensors/biometric_sensor.py` is missing (though defined in Spec).
    *   VAD thresholds are hardcoded and likely need user-specific calibration.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: Signal Calibration & Tuning
*   **Goal**: Reduce false positives for "Speech" (fan noise) and "Activity" (shadows).
*   **Deliverable**:
    1. Tuned heuristics in `AudioSensor` and `VideoSensor`.
    2. A `tools/calibrate_sensors.py` script that measures ambient background noise/light and updates `config.json` thresholds.
*   **Success Metric**: `calibrate_sensors.py` runs and successfully updates config; VAD does not trigger on silence/typing.

### 🎯 Milestone 2: Scenario Coverage (Logic "Lock-In")
*   **Goal**: Ensure core interventions trigger reliably without regression.
*   **Deliverable**: Three robust test scenarios using `ReplayHarness`:
    1. `test_doom_scroll.json`: Phone usage context -> Warning -> Intervention.
    2. `test_tic_flare.json`: Repeated rapid movement/sniffing -> Breathing exercise.
    3. `test_focus_drift.json`: Low focus state -> Gentle nudge.
*   **Success Metric**: All 3 scenarios pass consistently in CI/Test harness.

### 🎯 Milestone 3: LMM Hardening
*   **Goal**: Make the "Brain" resilient to internet flakiness and API errors.
*   **Deliverable**: `LMMInterface` update with:
    1. **Circuit Breaker**: Stop calling API after 3 failures.
    2. **Fallback Logic**: Use local heuristic logic if LMM is down.
    3. **Schema Enforcement**: Robust JSON parsing that handles "markdown block" wrapping from LLMs.
*   **Success Metric**: Unit test `test_lmm_resilience.py` passes with mocked network timeouts.

### 🎯 Milestone 4: Implement Biometric Sensor
*   **Goal**: Connect the "Body" (Heart Rate/Steps) to the Logic Engine.
*   **Deliverable**: `sensors/biometric_sensor.py` that watches `user_data/biometrics.json` for updates.
*   **Success Metric**: `LogicEngine` receives "High Heart Rate" signal when the JSON file is updated.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **Biometric Latency** | Low | Verify file-watch polling doesn't consume CPU. Use simple `os.stat` checks. |
| **VAD vs. Typing** | Med | Typing noise has high ZCR (like consonants). May need "Keystroke Filter" if simple VAD fails. |
| **LMM Costs/Rate Limits** | Med | Implement the "Circuit Breaker" (Milestone 3) to prevent runaway API bills/bans. |
| **Privacy (Biometrics)** | High | Ensure `biometrics.json` is in `.gitignore` and never logged to console. |

## 4. Backlog (Prioritized)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Create BiometricSensor** | Missing core spec component. | Class reads JSON; integrates into `LogicEngine`. | M | Low | Navigator |
| **LMM Circuit Breaker** | Reliability/Cost safety. | Stops requests after N errors; resets after time T. | S | Low | Navigator |
| **Calibrate Sensors Tool** | User-specific accuracy. | Script updates `config.json` with ambient baselines. | M | Low | Calibrator |
| **Scenario: Doom Scroll** | Verify logic without hardware. | JSON dataset exists; passes `ReplayHarness`. | S | Low | Testsmith |
| **Scenario: Tic Flare** | Verify logic without hardware. | JSON dataset exists; passes `ReplayHarness`. | S | Low | Testsmith |
| **Refine VAD Heuristics** | Too many false positives? | Tune ZCR/Pitch thresholds based on real mic test. | M | Med | Sentinel |
| **Log Rotation Policy** | Disk space safety. | `config.LOG_MAX_BYTES` is respected. | S | Low | Scribe |
| **Tray Tooltip Stats** | Better UX/Debugging. | Hovering icon shows current 5D State. | S | Low | Navigator |
| **Optimize Video Loop** | Reduce CPU usage. | Profile `VideoSensor`; ensure sleep if no change. | L | Med | Profiler |
| **Secure API Keys** | Security. | Ensure `.env` loading is robust; warn if missing. | S | Low | Navigator |
