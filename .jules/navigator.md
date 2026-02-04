## 2026-01-26 - [UX Feedback Fix]
**Learning:** `core/system_tray.py` had support for specific feedback icons (`feedback_helpful`, `feedback_unhelpful`) pre-implemented, but `main.py` was not using them, defaulting to flashing the current mode. This highlights a gap between component implementation and integration.
**Action:** Updated `main.py` to use the correct status keys. Added `tests/test_main_feedback_calls.py` to verify the integration, mocking heavy dependencies to isolate `main.py`.
**Hygiene:** Verified that `core/system_tray.py` indeed supports these keys to avoid runtime errors.

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

## 2026-01-22 - [LMM Timeout & Repo Hygiene]
**Learning:** `tools/generate_timeline.py` and `sensors/video_sensor.py` contained severe duplication artifacts (concatenated file versions), causing syntax errors and crashes in unrelated tests. This indicates a recurring hygiene issue with merge resolution.
**Action:** Cleaned up both files to strictly modular implementations. Implemented `tests/test_lmm_timeout.py` to verify LMM fallback logic, confirming that `LogicEngine` correctly handles LMM timeouts by opening the circuit breaker and triggering offline interventions.
**Pitfall:** Python `unittest.mock.patch` decorators pass arguments in reverse order (bottom-up), which can lead to confusing test failures if mocks are swapped.

## 2026-01-30 - [Context Intelligence - Active Window]
**Learning:** While `WindowSensor` was implemented and collecting data, the `LMMInterface` was not using this data in the prompt construction. This meant the "Context Intelligence" milestone was effectively stalled at the integration layer.
**Action:** Updated `core/lmm_interface.py` to inject `active_window` into the prompt and updated `core/prompts/v1.py` with guidance for the LLM. Added `tests/test_lmm_interface.py` verification.
**Hygiene:** Test execution failed initially due to missing `python-dotenv` in the environment. Ensuring `pip install -r requirements.txt` is run before testing is critical in this environment.

## 2026-02-05 - [Context History Implementation]
**Learning:** When writing tests that mock `config` via `sys.modules['config']`, simply assigning a `MagicMock` is insufficient if the code under test uses `getattr(config, 'KEY', default)`. `getattr` on a `MagicMock` returns a new `MagicMock` instead of the default value, causing `TypeError` when that value is expected to be an int (e.g., in `deque(maxlen=...)`).
**Action:** Always explicitly set the attributes on the mock config object (e.g., `mock_config.HISTORY_SIZE = 10`) or use a concrete object/dict instead of a bare `MagicMock`.
**Pitfall:** Reloading modules that import `numpy` (like `core.logic_engine`) inside a test using `sys.modules` patching can trigger `ImportError: cannot load module more than once per process` in `numpy` core.
**Mitigation:** Mock `cv2` and `numpy` in `sys.modules` alongside the target module to prevent actual `numpy` re-import attempts during the test.
