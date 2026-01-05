## 2024-05-24 - [Initial Run]
**Learning:** Initial setup of the navigator journal.
**Action:** Created the journal file.

## 2026-01-05 - [Shutdown Reliability]
**Learning:** `sounddevice` blocking reads prevent thread joins if not explicitly interrupted. Relying on `daemon=True` is insufficient for clean shutdown. Also, discovered that `InterventionEngine` suppression logic was flawed when using ID-based interventions because the local `type` variable wasn't updated from the library card.
**Action:** Refactored `main.py` to release sensors before joining threads. Fixed `VideoSensor` error state logic. Fixed `InterventionEngine` type resolution. Added `tools/verify_crash.py`.
