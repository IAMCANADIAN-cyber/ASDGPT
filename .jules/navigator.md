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

## 2026-01-14 - [Roadmap Drift]
**Learning:** The `ROADMAP.md` was significantly out of sync with the codebase. Features like Flow State Scenario, Face Posture Metrics, and Tray Icon State were implemented but listed as backlog or next steps.
**Action:** Updated `ROADMAP.md` to match reality. Added `tests/test_lmm_vad_context.py` to verify VAD signal propagation, closing Milestone 3 validation.
**Pitfall:** Agents relying solely on `ROADMAP.md` might re-implement existing features. Always verify file existence before starting "New" work.
