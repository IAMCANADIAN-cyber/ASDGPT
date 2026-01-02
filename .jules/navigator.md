## 2024-05-24 - [Initial Run]
**Learning:** Initial setup of the navigator journal.
**Action:** Created the journal file.

## 2026-01-02 - [Intervention Library & Harness]
**Learning:** Testing the `InterventionEngine` end-to-end is difficult without a dedicated harness because it involves threads, time delays, and side effects (TTS/Sound). A dedicated replay harness (`tools/intervention_replay_harness.py`) that mocks these side effects and accelerates time (where possible) is essential for verifying sequence logic and interruption handling.
**Action:** Created `tools/intervention_replay_harness.py` and used it to verify Milestone 2.
**Learning:** LMM reliability improves significantly when "grounded" to specific IDs. By injecting the list of available intervention IDs into the system prompt, we ensure the LMM outputs valid actions that the system can execute, rather than hallucinating generic advice.
**Action:** Updated `LMMInterface` system instruction to include the library's intervention IDs.

## 2026-01-02 - [Async LMM Processing]
**Learning:** `LogicEngine` was synchronously waiting for `LMMInterface` (local LLM calls), which froze the main loop for seconds, causing sensor data drops and UI lag.
**Action:** Refactored `LogicEngine` to run LMM analysis in a background thread (`_run_lmm_analysis_async`). Added `tests/test_async_logic.py` to verify non-blocking behavior.

## 2026-01-02 - [Timeline Correlation]
**Learning:** Interpreting the "black box" of LMM decisions is difficult without a unified view of sensor inputs, triggers, state updates, and interventions over time.
**Action:** Created `tools/generate_timeline.py` to parse logs and generate a markdown timeline report. This allows visualizing the cause-and-effect chain.
## 2026-01-02 - [LMM Benchmark]
**Learning:** High latency in the LMM loop is a critical risk for an "always-on" co-regulator. A dedicated benchmark script (`tools/lmm_benchmark.py`) is needed to continuously monitor round-trip times and catch regressions.
**Action:** Created `tools/lmm_benchmark.py` and validated it with a mock mode. Future runs should run this against the actual local LLM to verify the <2s latency target.
