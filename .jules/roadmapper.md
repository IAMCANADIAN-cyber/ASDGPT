# Roadmapper Journal

**Date:** 2024-06-05

## Critical Learnings
*   **Velocity Increase**: The completion of `tools/replay_harness.py` is a game-changer. We can now iterate on logic without needing to make noise or move around in front of a camera.
*   **Missing "Body"**: The `biometric_sensor.py` mentioned in the mental model was found to be missing from the codebase. This is a critical gap for the "Physiology" intervention category.
*   **Heuristic Limitations**: The current VAD and Posture detection are purely heuristic (math-based). They are fast but dumb. We need to plan for a transition to ML-based classifiers (e.g., MediaPipe) if false positives become a user complaint, but for now, we will optimize the heuristics (Milestone 1).

## Weekly Refresh (2024-06-05)
*   **Status Change**: Project moved from "Building Skeleton" to "Refining Reflexes".
*   **Focus Shift**: The priority is now on *Accuracy* and *Reliability*. It's better to trigger *less* often but *correctly* than to spam the user.
*   **Process Update**: All new feature logic *must* be accompanied by a `ReplayHarness` scenario test case.
