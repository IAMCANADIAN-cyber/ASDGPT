## 2024-05-24 - [Initial Run]
**Learning:** Initial setup of the navigator journal.
**Action:** Created the journal file.

## 2026-01-13
**Learning:** `LogicEngine` relies on internal fallback logic when sensors are `None`. To test advanced scenarios like VAD triggers without raw audio, one must inject mock sensors via the constructor, which `ReplayHarness` now supports.
**Action:** Updated `tools/replay_harness.py` to inject `MockAudioSensor` and `MockVideoSensor` and use `input_analysis` from scenario steps.
