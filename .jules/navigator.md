## 2024-05-24 - [Initial Run]
**Learning:** Initial setup of the navigator journal.
**Action:** Created the journal file.

## 2026-01-02 - [Intervention Library & Harness]
**Learning:** Testing the `InterventionEngine` end-to-end is difficult without a dedicated harness because it involves threads, time delays, and side effects (TTS/Sound). A dedicated replay harness (`tools/intervention_replay_harness.py`) that mocks these side effects and accelerates time (where possible) is essential for verifying sequence logic and interruption handling.
**Action:** Created `tools/intervention_replay_harness.py` and used it to verify Milestone 2.
**Learning:** LMM reliability improves significantly when "grounded" to specific IDs. By injecting the list of available intervention IDs into the system prompt, we ensure the LMM outputs valid actions that the system can execute, rather than hallucinating generic advice.
**Action:** Updated `LMMInterface` system instruction to include the library's intervention IDs.
