# Roadmapper Journal

**Date:** 2026-01-22

## Critical Learnings
*   **Vision vs. Reality Gap**: The `MENTAL_MODEL.md` is significantly ahead of the codebase. The doc describes a complex 5-dimensional state machine, while the code is currently a simple "loud noise = trigger" loop.
*   **LMM Dependency**: The entire "smart" part of the system relies on `LMMInterface` correctly parsing sensor data into the 5D state. This is currently a placeholder and is the highest risk component.
*   **Sensor Fidelity**: The current `video_activity` (pixel difference) and `audio_level` (RMS) are likely too crude to derive the subtle signals (like "shallow breathing" or "fidgeting") required by the Mental Model. We will likely need to integrate libraries like MediaPipe (for pose/face) and more advanced audio analysis.

## Strategic Pivot
*   Shift focus from "adding more features" (like OS telemetry) to **"deepening the core"**.
*   We must implement the `StateEngine` and robust Feature Extraction before the system can actually be an "Autonomous Co-Regulator". Currently, it's just a motion/noise detector.

## Weekly Refresh (2024-05-29)
*   **Outdated Docs**: `ROADMAP.md` was found to be stale (dated May 22). Regular updates are critical for agent alignment.
*   **Testing Gap**: Verified that while `tools/` exists, there is no robust "Replay Harness" to test `LogicEngine` decisions deterministically. This is a blocker for high-velocity iteration.
*   **Milestone Alignment**: Previous milestones (5D State, Intervention Library) are effectively "Done" in terms of skeletal code, but "In Progress" in terms of tuning/fidelity.

## Weekly Refresh (2026-01-22)
*   **LMM Fragility**: While the "Happy Path" works, the system is too fragile if the LMM is slow or offline. **Resilience** via fallback logic is now a top priority.
*   **Calibration Necessity**: Hardcoded thresholds in `config.py` are causing false positives (VAD, Motion) in different environments. We need a "Calibration Wizard" (Milestone 1) to personalize these.
*   **Scenario ROI**: The `scenarios/` tests (like `test_doom_scroll`) are proving to be the highest-ROI investment for verifying complex logic. We will double down on "Scenario-Driven Development" (e.g., `test_meeting_mode`).

## Weekly Refresh (2026-01-29)
*   **Calibration Success**: The "Calibration Wizard" assumption was correct; it is now live (`tools/calibrate.py`) and allows users to set personalized baselines.
*   **Heuristics Win**: The "Meeting Mode" heuristic (Speech + Face + Idle) proved effective, validating that complex high-level states can often be approximated by composite low-level signals without deep ML models.
*   **Pivot to Context**: With resilience established, the next friction point is "Context". The system treats "Coding" the same as "Watching Netflix". Detecting active windows (`WindowSensor`) is the critical next step to differentiate productivity from passivity.
*   **Efficiency**: As we add more sensors, `VideoSensor` CPU usage is becoming a concern. "Eco Mode" (Dynamic FPS) is necessary to keep the lightweight promise.
