# Dataset Curator Journal

## Learnings

### Synthetic Dataset Generation
- Created a synthetic dataset (`datasets/synthetic_events.json`) with 32 events.
- Events cover three main scenarios: "stress_spike" (high audio), "pacing" (high video activity), and "silence" (low inputs), plus some edge cases.
- Synthetic data allows for privacy-respecting evaluation without needing real user data.
- The dataset defines input metrics (audio level, video activity) and expected outcomes (trigger reason, state change, intervention type).

### Replay Harness
- Developed `tools/replay_harness.py` to evaluate the system using the synthetic dataset.
- The harness bypasses raw sensors but injects data into the `LogicEngine` in a way that exercises the signal processing logic (e.g., generating video frames with specific difference means).
- Mocked `LMMInterface` to return deterministic analysis based on the event's "expected outcome", allowing us to test the `LogicEngine` -> `LMM` -> `StateEngine` pipeline flow.
- The harness provides a report with metrics: accuracy (match rate between expected and actual interventions) and simulated intervention rate.

### Metrics & Evaluation
- The current synthetic set achieves 100% accuracy on the current logic. This serves as a regression test suite.
- If logic changes (e.g., thresholds), this harness will immediately highlight discrepancies.
- "False positives" in this context mean the system triggered an intervention when none (or a different one) was expected.

## Usage

To run the evaluation:
```bash
python tools/replay_harness.py
```

To regenerate the dataset:
```bash
python tools/generate_dataset.py
```
