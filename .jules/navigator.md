
## 2026-01-26 - [UX Feedback Fix]
**Learning:** `core/system_tray.py` had support for specific feedback icons (`feedback_helpful`, `feedback_unhelpful`) pre-implemented, but `main.py` was not using them, defaulting to flashing the current mode. This highlights a gap between component implementation and integration.
**Action:** Updated `main.py` to use the correct status keys. Added `tests/test_main_feedback_calls.py` to verify the integration, mocking heavy dependencies to isolate `main.py`.
**Hygiene:** Verified that `core/system_tray.py` indeed supports these keys to avoid runtime errors.

2026-01-29 - [Unit Testing Pitfall]
**Pitfall:** Using `patch.dict(sys.modules, ...)` to mock `keyboard` when importing `main` caused `main` to be re-imported later by `patch('main.DataLogger')`, triggering `numpy` initialization errors ("cannot load module more than once").
**Solution:** Do not import the module under test *inside* the `patch.dict` context if you plan to patch its attributes later. Or, patch `sys.modules` in `setUp` so it persists for the duration of the test methods where patches are applied.
