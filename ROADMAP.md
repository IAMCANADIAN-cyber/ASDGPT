# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-02-12
**Status:** ACTIVE

## 🗺️ Executive Summary
The system has successfully integrated **Context History** and **Reflexive Triggers**, enabling both deep narrative understanding and instant reactions.
The focus for this week shifts from "New Features" to **"Hardening & Control"**. We must ensure the system respects privacy (scrubbing history), works on more platforms (Wayland), and gives users granular control over what constitutes "Focus" vs. "Distraction".

## 1. Change Summary (Last 7 Days)
*   **Merged**: **Context Intelligence V2 (History)**: `LogicEngine` now maintains a sliding window of session history, providing the LMM with a "narrative" view.
*   **Merged**: **Reflexive Triggers V2**: `LogicEngine` now supports immediate, rule-based interventions for specific windows (e.g., games), bypassing LMM latency.
*   **Merged**: **Reliability Fix**: Critical deadlock in `VideoSensor` during shutdown was resolved.
*   **Verified**: **Test Harness**: `tools/replay_harness.py` is functional and ready for tuning tasks.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: Privacy & Platform Hardening
*   **Goal**: Ensure the system is safe to use on personal devices and supports modern Linux environments.
*   **Deliverable**:
    1. `WindowSensor` support for Wayland (or graceful fallback).
    2. **Privacy Scrubber**: Automatically redact sensitive window titles (e.g., "Bank", "Password") *before* they enter Context History.
*   **Success Metric**: `WindowSensor` works on Wayland; Sensitive keywords are replaced with "[REDACTED]" in logs/history.

### 🎯 Milestone 2: User Control V2 (Configurability)
*   **Goal**: Allow users to easily define their own "Focus" and "Distraction" apps without editing code.
*   **Deliverable**:
    1. Refactored `config.py` to load "Focus/Distraction" lists from `user_data/config.json`.
    2. Updated `tools/config_gui.py` to support editing these lists.
*   **Success Metric**: User can add a custom game to the blacklist via GUI/JSON and have it trigger immediately.

### 🎯 Milestone 3: Tuning with Harness
*   **Goal**: Reduce false positives for "Doom Scrolling" and "Distraction" triggers.
*   **Deliverable**:
    1. A synthetic dataset (`datasets/doom_scroll.json`) for the Replay Harness.
    2. Tuned thresholds/prompts based on harness results.
*   **Success Metric**: >90% accuracy on "Doom Scroll" detection in the harness.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **Wayland Support** | High | `xprop` fails on Wayland. Investigate `gnome-shell` extensions or `kwin` scripts. Fallback to "Unknown" if necessary. |
| **LMM Hallucinations (History)** | Med | With more text context, LMM might invent patterns. Tune system prompt to be strictly factual about history. |
| **Performance (String Ops)** | Low | History formatting adds string overhead. Profile `_prepare_lmm_data` to ensure it stays <5ms. |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Implement Privacy Scrubber** | User Trust. | Window titles matching sensitive keywords are redacted in `LogicEngine`. | S | Low | Sentinel |
| **Add Wayland Support** | Linux Compat. | `WindowSensor` detects active window on Wayland (GNOME/KDE). | L | High | Navigator |
| **Update Config GUI** | Usability. | `config_gui.py` allows editing `REFLEXIVE_WINDOW_TRIGGERS`. | M | Low | Scribe |
| **Create 'Doom Scroll' Dataset** | Tuning. | `datasets/doom_scroll.json` exists with realistic event sequences. | S | Low | Testsmith |
| **Refine LMM Prompt for History** | Accuracy. | System prompt includes specific instructions on interpreting "Recent History". | S | Low | Navigator |
| **Profile Window Sensor** | Performance. | Ensure `get_active_window` latency is acceptable (<50ms). | S | Low | Profiler |
| **Audit Sensitive Keywords** | Privacy. | Expand default `SENSITIVE_APP_KEYWORDS` list. | S | Low | Sentinel |
| **Unit Test Context History** | Reliability. | `test_logic_engine_history.py` covers edge cases (empty history, rapid switching). | S | Low | Testsmith |
| **Add 'Game Mode' Trigger** | User Value. | Pre-configured reflex triggers for popular launchers (Steam, Epic). | S | Low | Sentinel |
| **Update User Guide** | Documentation. | `README.md` explains how to configure Reflexive Triggers. | S | Low | Scribe |
