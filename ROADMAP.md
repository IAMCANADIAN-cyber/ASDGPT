# ASDGPT Weekly Roadmap Refresh

**Date:** 2024-06-05
**Status:** ACTIVE

## 🗺️ Executive Summary
The ASDGPT project has achieved significant milestones in **System Reliability**, **Evaluation Infrastructure**, and **UX**. The focus now shifts to **Signal Quality Refinement** and utilizing the new VAD capabilities to drive better interventions. We have confirmed the system is robust (crash tests passed), DND mode is fully functional, and we have a working replay harness.

## 1. Change Summary (Last 7 Days)
*   **Completed**: `verify_crash.py` confirms system reliability (10/10 cycles passed).
*   **Completed**: `test_doom_scroll.py` passes using the new `replay_harness`.
*   **Completed**: **DND Mode** (Milestone 4) is fully implemented and tested.
*   **Merged**: VAD integration into `AudioSensor`, providing `speech_rate` and `speech_confidence` metrics.
*   **Improved**: LMM Context now utilizes real VAD metrics (Syllables/sec, Voice Activity) instead of legacy approximations.
*   **Completed**: Added `tests/scenarios/test_panic_attack.py` to verify critical intervention logic.
*   **Completed**: Added `tests/scenarios/test_flow_state.py` to verify Flow State detection.
*   **Completed**: Verified VAD Signal Propagation with `tests/test_lmm_vad_context.py`.
*   **Verified**: Log Rotation, Tray Icon State, and Face Posture Metrics are implemented and active.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: System Reliability & Graceful Shutdown
*   **Status**: ✅ COMPLETED (Verified by `verify_crash.py`)
*   **Next Steps**: Monitor for long-term stability in `custom_logs/`.

### 🎯 Milestone 2: Evaluation Harness V1
*   **Status**: ✅ COMPLETED (Verified by `test_doom_scroll.py`, `test_panic_attack.py`, `test_flow_state.py`)
*   **Next Steps**: Expand scenarios to include "Intimacy" and "Content Creation" trajectories.

### 🎯 Milestone 3: Signal Quality - Voice Activity Detection (VAD)
*   **Status**: ✅ VERIFIED (Signal Propagation)
*   **Goal**: Ensure LMM effectively uses the new `speech_rate` and `voice_activity` signals.
*   **Deliverable**: Verified prompt construction via `tests/test_lmm_vad_context.py`.
*   **Next Steps**: Calibrate `VAD_SILENCE_THRESHOLD` with real-world user data.

### 🎯 Milestone 4: UX - "Do Not Disturb" Mode
*   **Status**: ✅ COMPLETED
*   **Deliverable**: "Focus Mode" / "DND" toggle in System Tray and `LogicEngine`.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **LMM Latency** | Med | Monitor `LMMInterface` response times. Consider smaller local models if >5s. |
| **VAD False Positives** | Med | Calibrate `AudioSensor` thresholds (`VAD_SILENCE_THRESHOLD`) in real-world usage. |
| **Performance** | Low | Profiling needed for `VideoSensor` on lower-end hardware. |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Unit Test Coverage** | Stability. | `pytest` coverage > 80% for `core/`. | M | Low | Testsmith |
| **Scenario Expansion** | Better eval. | Add "Intimacy" and "Content Creation" scenarios to `test_new_modes.py` (Basic triggers exist). | M | Low | Testsmith |
| **UI Polish** | UX. | Add icons for new modes (Intimacy, Content Creation). | S | Low | Designer |
