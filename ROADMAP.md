# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-01-22
**Status:** ACTIVE

## 🗺️ Executive Summary
The ASDGPT project has solidified its core pillars: **System Reliability** (crashes resolved), **Evaluation** (replay harness functional), and **Signal Quality** (VAD and Face Posture active).
The focus for this week shifts to **Resilience** and **Personalization**. We must ensure the system works even when the LMM is slow or offline (Fallback Mode), and that sensor thresholds adapt to the user's environment (Calibration).

## 1. Change Summary (Last 7 Days)
*   **Completed**: `verify_crash.py` confirms system reliability (10/10 cycles passed).
*   **Completed**: `test_doom_scroll.py` passes using the new `replay_harness`.
*   **Completed**: **DND Mode** (Milestone 4) is fully implemented and tested.
*   **Merged**: VAD integration into `AudioSensor`, providing `speech_rate` and `speech_confidence` metrics.
*   **Improved**: LMM Context now utilizes real VAD metrics (Syllables/sec, Voice Activity) instead of legacy approximations.
*   **Completed**: Added `tests/scenarios/test_panic_attack.py` to verify critical intervention logic.
*   **Completed**: Added `tests/scenarios/test_flow_state.py` to verify Flow State non-intervention logic.
*   **Completed**: VAD Refinement validation (`tests/test_vad_refinement.py`) passes, confirming suppression of fan noise and typing sounds.
*   **Completed**: Verified **Face Posture Metrics** implementation (`tests/test_video_metrics.py`) and verified end-to-end scenario (`tests/scenarios/test_posture_correction.py`).
*   **Verified**: **Tray Icon State** tooltip correctly displays internal state (Arousal, Energy, etc.).
*   **Completed**: **Face Posture Metrics**: `VideoSensor` outputs head tilt and slouch estimates (`face_roll_angle`, `posture_state`).
*   **Completed**: **Tray Icon State**: Tooltip now shows dynamic 5-dimension state ("A: 60 O: 0...").
*   **Completed**: **Log Rotation**: `DataLogger` uses `RotatingFileHandler` to prevent indefinite log growth.
*   **Completed**: **LMM Latency Monitoring**: `LMMInterface` now logs request latency and includes it in response metadata.
*   **Merged**: **VAD Integration**: `AudioSensor` now provides `speech_rate` and `voice_activity`, replacing crude volume thresholds.
*   **Merged**: **Face Posture Metrics**: `VideoSensor` detects `face_roll_angle` (tilt) and `posture_state` (slouching).
*   **Merged**: **LMM Latency Tracking**: Request times are logged and monitored; LMM context now includes real VAD data.
*   **Verified**: **Reliability**: `verify_crash.py` passed 10/10 cycles; `test_doom_scroll` and `test_panic_attack` scenarios confirmed logic.
*   **Completed**: **DND Mode**: "Do Not Disturb" is functional and testable.
*   **Completed**: **Log Rotation**: Prevented disk fill-up issues with `RotatingFileHandler`.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: Signal Calibration (Personalization)
*   **Goal**: Replace hardcoded `config.py` thresholds with user-specific baselines.
*   **Deliverable**: A `CalibrationEngine` (or "Wizard" script) that samples environment for 30s to set `VAD_SILENCE_THRESHOLD` and `BASELINE_POSTURE`.
*   **Success Metric**: `config.json` is updated with personalized values; reduced VAD false positives in quiet rooms.

### 🎯 Milestone 2: Evaluation Harness V1
*   **Status**: ✅ COMPLETED (Verified by `test_doom_scroll.py`, `test_panic_attack.py`, `test_flow_state.py`, `test_posture_correction.py`)
*   **Next Steps**: Add more complex scenarios as needed.
### 🎯 Milestone 2: LMM Offline Fallback (Resilience)
*   **Goal**: Ensure "basic safety" interventions work even if the LMM is down or timing out (>10s).
*   **Deliverable**: `LogicEngine` fallback triggers (e.g., if `LMM_TIMEOUT`, use simple `High Noise -> Reduction` rule).
*   **Success Metric**: System successfully triggers an intervention during an induced LMM timeout in tests.

### 🎯 Milestone 3: "Meeting Mode" Detection (Context Awareness)
*   **Goal**: Prevent embarrassing interruptions during calls/meetings.
*   **Deliverable**: Heuristic detection: `Continuous Speech` + `Face Present` + `No Keyboard` = `Meeting` -> Auto-DND.
*   **Success Metric**: New scenario `test_meeting_mode.py` passes.

### 🎯 Milestone 4: UX Feedback Loop (Interaction)
*   **Goal**: Confirm to the user that their "Helpful/Unhelpful" feedback was registered.
*   **Deliverable**: Visual toast/notification or Tray Icon flash on hotkey press.
*   **Success Metric**: User receives immediate visual confirmation of feedback actions.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **LMM Latency** | Med | ✅ Monitored in `LMMInterface`. Check logs for latency > 5s. |
| **VAD False Positives** | Med | Calibrate `AudioSensor` thresholds (`VAD_SILENCE_THRESHOLD`) in real-world usage. |
| **Performance** | Low | Profiling needed for `VideoSensor` on lower-end hardware. |
| **LMM Context Window** | Med | Monitor token usage as we add VAD/Posture history. Prune history if needed. |
| **Sensor CPU Load** | Low | Profile `VideoSensor` with new Posture logic. Consider "Eco Mode" (lower FPS). |
| **False Positives (VAD)** | Med | Typing/Fan noise triggers. Mitigate via Milestone 1 (Calibration). |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Personalized Baselines** | Improve accuracy. | `StateEngine` loads baseline from user profile. | M | Low | Architect |
| **Web Dashboard** | Visualization. | Simple local web UI for `events.jsonl`. | L | Med | UI/UX |
| **Unit Test Coverage** | Stability. | `pytest` coverage > 80% for `core/`. | M | Low | Testsmith |
| **Calibration Wizard Script** | "Normal" noise varies wildy. | `tools/calibrate.py` runs, updates `user_data/config.json`. | M | Low | Calibrator |
| **Audio Calibration Logic** | Core logic for noise floor. | `AudioSensor.calibrate()` returns valid threshold. | S | Low | Calibrator |
| **Video Calibration Logic** | Core logic for neutral posture. | `VideoSensor.calibrate()` returns baseline tilt. | S | Low | Calibrator |
| **LMM Fallback Trigger** | Single point of failure. | LogicEngine detects `LMM_TIMEOUT` event. | S | Med | Sentinel |
| **Offline Intervention Logic** | Safety net when offline. | Simple noise-based intervention triggers without LMM. | M | Med | Sentinel |
| **Test LMM Timeout** | Verify fallback works. | `tests/test_lmm_timeout.py` passes. | S | Low | Testsmith |
| **Meeting Mode Logic** | Interruptions destroy trust. | Heuristic (Speech+Face+NoInput) defined in LogicEngine. | M | Med | Navigator |
| **Meeting Mode Scenario** | Verify meeting logic. | `test_meeting_mode.py` passes. | S | Low | Testsmith |
| **Visual Feedback (Toast)** | UX is opaque. | Notification shown on hotkey. | S | Low | Navigator |
| **Token Usage Logging** | Cost/Limit visibility. | `LMMInterface` logs input/output tokens. | S | Low | Profiler |
| **Prune Context Window** | Prevent overflow errors. | `LMMInterface` truncates history > N tokens. | M | Med | Profiler |
| **Video Eco Mode** | CPU usage is high. | Reduce FPS to 1 when no face detected. | M | Low | Profiler |
| **Update README.md** | Entry point is stale. | Installation/Run steps are verified current. | S | Low | Scribe |
| **Type Hinting Core** | Reduce runtime errors. | `core/logic_engine.py` fully typed. | M | Low | Sentinel |
| **Dependency Audit** | Bloat reduction. | `requirements.txt` cleaned of unused libs. | S | Low | Scribe |
