# Roadmapper Journal

**Date:** 2024-05-22

## Critical Learnings
*   **Vision vs. Reality Gap**: The `MENTAL_MODEL.md` is significantly ahead of the codebase. The doc describes a complex 5-dimensional state machine, while the code is currently a simple "loud noise = trigger" loop.
*   **LMM Dependency**: The entire "smart" part of the system relies on `LMMInterface` correctly parsing sensor data into the 5D state. This is currently a placeholder and is the highest risk component.
*   **Sensor Fidelity**: The current `video_activity` (pixel difference) and `audio_level` (RMS) are likely too crude to derive the subtle signals (like "shallow breathing" or "fidgeting") required by the Mental Model. We will likely need to integrate libraries like MediaPipe (for pose/face) and more advanced audio analysis.

## Strategic Pivot
*   Shift focus from "adding more features" (like OS telemetry) to **"deepening the core"**.
*   We must implement the `StateEngine` and robust Feature Extraction before the system can actually be an "Autonomous Co-Regulator". Currently, it's just a motion/noise detector.
