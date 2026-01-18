## 2024-05-24 - [Initial Run]
**Learning:** Initial setup of the navigator journal.
**Action:** Created the journal file.

## 2025-01-04 - [Upstream Collision on AudioSensor]
**Learning:** Another agent implemented VAD/ZCR in `AudioSensor` (likely `origin/main` updated) while I was refactoring it for threading. This caused a conflict where "Accept Incoming" was necessary to avoid feature regression (losing VAD), sacrificing the threading refactor for now.
**Action:** Accepted upstream changes via PR comment. Future refactors should verify upstream feature sets closely before rewriting entire classes.
