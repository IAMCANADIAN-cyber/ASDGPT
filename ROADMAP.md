# ASDGPT Weekly Roadmap Refresh

**Date:** 2024-05-29
**Status:** ACTIVE

## 🗺️ Executive Summary
The ASDGPT project has successfully implemented the core "skeleton" of the Autonomous Co-Regulator (ACR), including the 5D State Engine, Intervention Library, and a basic Feedback Loop. The focus now shifts from "building the body" to "refining the senses and reflexes." The next week is dedicated to **System Reliability**, **Signal Quality**, and **Evaluation**. We must ensure the system can run for hours without crashing and that interventions are triggered by meaningful signals, not just noise.

## 1. Change Summary (Last 7 Days)
*   **Merged**: `navigator-context-persistence-loop` (PR #70). This established the feedback loop where user hotkey inputs (Helpful/Unhelpful) persist to disk and influence future interventions.
*   **State**:
    *   `StateEngine` now tracks Arousal, Overload, Focus, Energy, Mood.
    *   `InterventionLibrary` v1 is live with Physiology, Sensory, Cognitive, and Creative categories.
    *   `LMMInterface` is wired to inject user context (suppressions, preferences) into prompts.
*   **Gaps**:
    *   `ROADMAP.md` was outdated.
    *   No end-to-end "replay harness" to test logic without hardware.
    *   Video/Audio features are still basic (RMS/Pixel Diff) and prone to false positives.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: System Reliability & Graceful Shutdown
*   **Goal**: Eliminate "zombie threads" and resource leaks. Ensure the app can be started and stopped repeatedly without error.
*   **Deliverable**: robust `shutdown()` in `main.py` and `LogicEngine`, handling thread joins and sensor release (especially `sounddevice`).
*   **Success Metric**: `verify_crash.py` (or similar stress test) passes 10/10 rapid start/stop cycles.

### 🎯 Milestone 2: Evaluation Harness V1
*   **Goal**: Enable "hardware-free" logic testing. We need to simulate a "Doom Scroll" scenario and verify the system triggers the correct intervention *before* we run it on a real user.
*   **Deliverable**: `tools/replay_harness.py` capable of feeding synthetic `audio_chunk` and `video_frame` sequences to `LogicEngine`.
*   **Success Metric**: A test case `tests/scenarios/test_doom_scroll.py` passes using the harness.

### 🎯 Milestone 3: Signal Quality - Voice Activity Detection (VAD)
*   **Goal**: Stop treating background noise as "User Activity".
*   **Deliverable**: Integrate a simple VAD (energy-based or webrtcvad) into `AudioSensor` to distinguish speech/action from silence/fan noise.
*   **Success Metric**: `AudioSensor` reports `is_speech=True` only for actual speech in a test recording.

### 🎯 Milestone 4: UX - "Do Not Disturb" Mode
*   **Goal**: Allow users to temporarily disable interventions without quitting the app (e.g., during meetings).
*   **Deliverable**: "Focus Mode" / "DND" toggle in System Tray and `LogicEngine`.
*   **Success Metric**: LogicEngine suppresses all interventions when DND is active.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **Thread Safety** | High | Review `_sensor_lock` usage in `main.py` and `InterventionEngine` to prevent race conditions. |
| **LMM Hallucinations** | Med | Strict schema validation in `LMMInterface` (already present, need to verify robustness with fuzzing). |
| **Sensor Locking** | High | `sounddevice` and `cv2` can lock up if not released properly. Prioritize Milestone 1. |
| **Performance** | Med | Profiling needed. Ensure `VideoSensor` isn't eating 100% CPU on the analysis thread. |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Implement VAD** | Reduce false positives from noise. | `AudioSensor.analyze_chunk` returns `speech_confidence`. | M | Low | Sentinel |
| **Replay Harness** | Essential for safe iteration. | Script runs `LogicEngine` with mock data. | L | Low | Testsmith |
| **DND Mode** | UX requirement for meetings. | Tray menu has "Toggle DND"; LogicEngine respects it. | S | Low | Navigator |
| **Fix Thread Joins** | Prevent application hang on exit. | `main.py` exits cleanly < 2s. | S | Med | Navigator |
| **LMM Circuit Breaker** | Prevent API spam on failure. | Stop calling LMM for 1m if 3 consecutive errors. | M | Low | Navigator |
| **Intervention Cooldown** | Prevent nagging. | Configurable global cooldown (e.g., 15 mins). | S | Low | Navigator |
| **Face Posture Metrics** | Better state estimation. | `VideoSensor` outputs head tilt/slouch estimate. | L | High | Calibrator |
| **Tray Icon State** | Visibility. | Tooltip shows "Arousal: 60, Energy: 40". | S | Low | Navigator |
| **Log Rotation** | Disk space management. | Logs don't grow indefinitely. | S | Low | Scribe |
| **Unit Test Coverage** | Stability. | `pytest` coverage > 60% for `core/`. | M | Low | Testsmith |
