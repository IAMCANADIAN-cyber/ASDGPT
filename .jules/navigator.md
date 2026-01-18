## 2024-05-24 - [Initial Run]
**Learning:** Initial setup of the navigator journal.
**Action:** Created the journal file.

## 2026-01-13
**Learning:** `LogicEngine` relies on internal fallback logic when sensors are `None`. To test advanced scenarios like VAD triggers without raw audio, one must inject mock sensors via the constructor, which `ReplayHarness` now supports.
**Action:** Updated `tools/replay_harness.py` to inject `MockAudioSensor` and `MockVideoSensor` and use `input_analysis` from scenario steps.
## 2026-01-12 - [Panic Attack Scenario]
**Learning:** `ReplayHarness` is a powerful tool for simulating complex state trajectories without real-time sensor input. However, using it requires careful setup of the `expected_outcome` dictionary to match the `LogicEngine`'s expectations.
**Action:** Implemented `tests/scenarios/test_panic_attack.py` to verify the 'meltdown_prevention' intervention trigger during a simulated panic attack (Escalating -> Critical).
**Pitfall:** `pytest` was not installed in the environment despite being a standard tool. Added explicit installation step.

## 2026-01-15 - [Flow State Verification]
**Learning:** `ReplayHarness` had a critical bug where `step_success` was overwritten by intervention verification results, masking state verification failures. Also, `StateEngine` applies smoothing (SMA over 5 frames), so test expectations must strictly account for this lag.
**Action:** Fixed `tools/replay_harness.py` to correctly aggregate success flags. Updated `tests/scenarios/test_flow_state.py` to include and verify `expected_state` with mathematically correct smoothed values.

## 2026-01-15 - [Posture Correction Scenario]
**Learning:** Verified that `VideoSensor` posture metrics (slouching, head tilt) were implemented but unverified in scenarios. Using `ReplayHarness`, I confirmed that `LogicEngine` correctly propagates these metrics to the LMM and that the system triggers `posture_water_reset` when slouching persists.
**Action:** Created `tests/scenarios/test_posture_correction.py` and updated `ROADMAP.md` to move Face Posture Metrics to completed.
## 2026-01-15 - [Roadmap Sync & Finalization]
**Learning:** Significant "Roadmap Drift" occurred where features like Face Posture Metrics, Tray Icon State, and Log Rotation were implemented and tested but remained in the "Backlog".
**Action:** Synchronized `ROADMAP.md` with the codebase state, moving completed items out of backlog. Verified that unit tests for these features (`tests/test_video_metrics.py`, `tests/test_tray_tooltip.py`, `tests/test_log_rotation.py`) are passing.

## 2026-01-16 - [Coverage & Hygiene]
**Learning:** `core/intervention_library.py` contained significant untested logic in an `if __name__ == "__main__":` block, bypassing unit tests. Also, `pytest-cov` generates a binary `.coverage` file which is not ignored by default, posing a repo hygiene risk.
**Action:** Refactored `intervention_library` to use a proper `unittest` suite (`tests/test_intervention_library.py`) and updated `.gitignore` to exclude coverage artifacts.
