# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-01-29
**Status:** ACTIVE

## 🗺️ Executive Summary
The ASDGPT project has successfully achieved **Resilience** (Offline Fallback) and **Personalization** (Calibration). The system can now adapt to its environment and gracefully handle LMM outages.
The focus for this week shifts to **Context Intelligence** and **Efficiency**. We need the system to understand *what* the user is doing (e.g., "Coding" vs. "Watching TV") to provide smarter interventions, and we need to reduce the resource footprint (CPU/Battery) when the user is idle.

## 1. Change Summary (Last 7 Days)
*   **Merged**: **Signal Calibration**: `CalibrationEngine` (`tools/calibrate.py`) is live, allowing users to set personalized VAD and Posture baselines.
*   **Merged**: **Offline Fallback**: `LogicEngine` now triggers simple heuristic interventions (e.g., "Noise Reduction") when the LMM circuit breaker is open.
*   **Merged**: **Meeting Mode**: Auto-DND is triggered by `Continuous Speech` + `Face Detected` + `Input Idle` heuristics.
*   **Merged**: **UX Feedback**: Users can provide "Helpful/Unhelpful" feedback via hotkeys, with immediate visual confirmation (Tray Icon flash).
*   **Verified**: **Reliability**: `test_meeting_mode.py` and `test_lmm_timeout.py` pass, confirming core logic resilience.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: Context Intelligence (App Awareness)
*   **Goal**: Enable the system to distinguish between "Deep Work" (e.g., VS Code, Word) and "Passive Consumption" (e.g., Netflix, YouTube).
*   **Deliverable**: A `WindowSensor` that captures and sanitizes the active window title/process name.
*   **Success Metric**: `LogicEngine` receives `active_window` context; LMM uses it to suppress interruptions during "Deep Work".

### 🎯 Milestone 2: Resource Optimization (Eco Mode)
*   **Goal**: Reduce background resource usage (CPU/Battery) when the user is not present or engaged.
*   **Deliverable**: Dynamic FPS in `VideoSensor`: Drop to 1Hz when no face is detected or system is idle, ramp to 30Hz immediately on motion.
*   **Success Metric**: CPU usage drops by >50% during idle periods; Wake-up latency < 200ms.

### 🎯 Milestone 3: Adaptive Policy (Smart Cooling)
*   **Goal**: Reduce annoyance by respecting user feedback.
*   **Deliverable**: `InterventionEngine` logic to suppress specific intervention *types* for a cooling period (e.g., 1 hour) after receiving "Unhelpful" feedback.
*   **Success Metric**: Repeated "Unhelpful" feedback for "Posture" stops Posture interventions for the session.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **Window Hook Compatibility** | Med | Verify `pygetwindow`/`ctypes` on target OS (Linux/Windows). Implement graceful failure (return "Unknown"). |
| **Eco Mode Wake-up** | Med | Ensure motion detection (diff) runs on the 1Hz frame to trigger "Wake Up" instantly. |
| **Privacy (Window Titles)** | High | Implement strict sanitization (Regex replace PII) or only categorize (Productivity/Entertainment) locally. |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Implement WindowSensor** | Context is key for "Doom Scroll" vs "Work". | `WindowSensor.get_active_window()` returns sanitized title. | M | Med | Navigator |
| **Video Eco Mode Logic** | Save battery/CPU. | FPS drops to 1Hz when idle; wakes on motion. | M | Low | Profiler |
| **Intervention Cooling** | Respect user agency. | "Unhelpful" feedback adds type to temporary suppression list. | S | Low | Sentinel |
| **Sanitize Window Titles** | Prevent PII leak to LMM. | Regex filter removes emails/filenames from titles. | S | Low | Sentinel |
| **Test Window Sensor** | Verify cross-platform stability. | `tests/test_window_sensor.py` passes (mocked OS calls). | S | Low | Testsmith |
| **Test Eco Mode** | Verify latency. | Test confirming transition 1Hz -> 30Hz on motion. | M | Med | Profiler |
| **LMM Context Pruning** | Cost/Stability. | Sliding window for `user_context` history. | M | Low | Profiler |
| **Update User Guide** | UX. | Document new Calibration and Feedback features in README. | S | Low | Scribe |
