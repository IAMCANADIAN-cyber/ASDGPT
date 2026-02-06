# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-02-05
**Status:** ACTIVE

## 🗺️ Executive Summary
The system has achieved basic **Context Awareness** (Active Window Detection) and **Efficiency** (Video Eco Mode). We are now moving to **Deep Context** and **Robustness**.
The focus for this week is to give the LMM a "memory" of recent actions (Context History) so it can detect trends, and to implement "Reflexive Triggers" that react instantly to specific apps without waiting for the LMM. We will also prioritize **Test Hygiene** to speed up development.

## 1. Change Summary (Last 7 Days)
*   **Merged**: **Context Intelligence V1**: `WindowSensor` is live, sanitizing and reporting the active window title.
*   **Merged**: **Resource Optimization**: `Video Eco Mode` (Dynamic FPS) is live in `main.py`, reducing idle CPU usage.
*   **Merged**: **Adaptive Policy**: `InterventionEngine` now supports "Cooling" (suppression) based on "Unhelpful" feedback.
*   **Merged**: **Test Hygiene**: Added `tools/cleanup.py` and `Makefile`. Verified `ReplayHarness` functionality.
*   **Consolidated**: Routine maintenance merges (test fixes, cleanup) have been consolidated into `main`.

## 2. Top Milestones (Next 7 Days)

### ✅ Milestone 1: Context Intelligence V2 (History) - COMPLETED
*   **Goal**: Enable the LMM to see the "narrative" of the user's session.
*   **Deliverable**: Sliding window history + Rapid Task Switching heuristics + String Truncation.
*   **Success Metric**: `tests/test_context_intelligence.py` passes; LMM receives truncated history and system alerts.

### 🎯 Milestone 2: Reflexive Triggers V2 (Window Rules)
*   **Goal**: Instant reaction to blacklisted apps (e.g., Games, Social Media) without LMM latency.
*   **Deliverable**: `LogicEngine` triggers specific interventions immediately when `active_window` matches a rule set.
*   **Success Metric**: Latency < 100ms for detecting and reacting to a blacklisted app.

### ✅ Milestone 3: Test Hygiene & Harness (Completed)
*   **Goal**: Eliminate "flaky" tests and repo clutter to improve developer velocity.
*   **Deliverable**: `tools/cleanup.py` to remove artifacts; verification of `tools/replay_harness.py`.
*   **Success Metric**: `make clean` works; Replay Harness runs a scenario successfully.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **LMM Token Cost/Latency** | Med | History adds tokens. Limit history to last 3-5 entries or summarize if needed. |
| **Privacy (History)** | High | Ensure `WindowSensor` sanitization is robust before storing in history. |
| **Reflexive vs. LMM Conflict** | Med | Ensure Reflexive Triggers (Tier 2/3) correctly preempt or inform LMM (Tier 1). |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Implement Context History** | LMM needs "narrative". | `user_context` includes `history` list in prompt. | M | Low | Navigator |
| **Implement Reflexive Window Triggers** | Fast reaction to games/distractions. | `LogicEngine` triggers on specific window titles. | M | Low | Sentinel |
| **Verify WindowSensor on Linux** | Cross-platform compatibility. | `xprop` returns correct titles on CI/Dev machine. | S | Med | Testsmith |
| **Refine LMM Prompt for History** | Teach LMM to use history. | System prompt includes instructions on "Recent History". | S | Low | Navigator |
| **Update User Guide** | Documentation. | `README.md` reflects Eco Mode and Window Sensor. | S | Low | Scribe |
| **Add Wayland Support** | Future-proofing Linux. | `WindowSensor` handles Wayland gracefully (or warns). | M | High | Navigator |
| **Audit Sensitive Keywords** | Privacy. | `config.py` includes more default sensitive apps. | S | Low | Sentinel |
| **Unit Test Context History** | Reliability. | `test_logic_engine_history.py` verifies state tracking. | S | Low | Testsmith |
| **Profile Window Sensor** | Performance. | Ensure `get_active_window` takes <50ms. | S | Low | Profiler |
| **Add 'Game Mode' Trigger** | User Value. | Detect 'Steam'/'Epic' and switch mode/suppress. | S | Low | Sentinel |
