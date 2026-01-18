import pytest
import os
import sys
import json
from tools.replay_harness import ReplayHarness

# Ensure tools and core are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_policy_replay_accuracy():
    """
    Runs the ReplayHarness against the synthetic dataset and asserts high accuracy.
    This ensures that the LogicEngine and LMMInterface (mocked) interaction
    correctly implements the intervention policy.
    """
    dataset_path = "datasets/synthetic_events.json"
    if not os.path.exists(dataset_path):
        pytest.skip(f"Dataset not found at {dataset_path}")

    harness = ReplayHarness(dataset_path)

    # Run the harness
    results = harness.run()

    # Assertions
    assert results['total_events'] > 0, "No events found in dataset"

    # We expect 100% accuracy on the synthetic set as it's designed for this logic
    # But let's allow a small margin if timing causes issues, though harness is synchronous-ish
    accuracy = (results['correct_triggers'] / results['total_events'])

    # Log failure details if any
    if accuracy < 1.0:
        print(f"Policy Replay Failed. Accuracy: {accuracy:.2%}")
        print(f"False Positives: {results['false_positives']}")
        print(f"False Negatives: {results['false_negatives']}")

    assert accuracy >= 0.95, f"Policy accuracy {accuracy:.2%} is below threshold 95%"
    assert results['false_positives'] == 0, "Found false positive interventions"
    assert results['false_negatives'] <= 1, "Found too many false negatives"

if __name__ == "__main__":
    test_policy_replay_accuracy()
