## 2024-05-24 - [Initial Run]
**Learning:** Initial setup of the navigator journal.
**Action:** Created the journal file.

## 2026-01-14
**Learning:** Mocking `sys.modules["config"]` in unit tests is dangerous because it poisons the module cache, causing subsequent tests (like `test_flow_state.py`) to fail when they expect real config attributes (e.g., `logging` levels).
**Action:** Refactored `tests/test_tray_tooltip.py` to import the real `config` module and patch attributes only where necessary, ensuring isolation and preventing `TypeError` in `DataLogger`.

## 2026-01-13
**Learning:** `LogicEngine` relies on internal fallback logic when sensors are `None`. To test advanced scenarios like VAD triggers without raw audio, one must inject mock sensors via the constructor, which `ReplayHarness` now supports.
**Action:** Updated `tools/replay_harness.py` to inject `MockAudioSensor` and `MockVideoSensor` and use `input_analysis` from scenario steps.
## 2026-01-12 - [Panic Attack Scenario]
**Learning:** `ReplayHarness` is a powerful tool for simulating complex state trajectories without real-time sensor input. However, using it requires careful setup of the `expected_outcome` dictionary to match the `LogicEngine`'s expectations.
**Action:** Implemented `tests/scenarios/test_panic_attack.py` to verify the 'meltdown_prevention' intervention trigger during a simulated panic attack (Escalating -> Critical).
**Pitfall:** `pytest` was not installed in the environment despite being a standard tool. Added explicit installation step.
