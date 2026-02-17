# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-02-19
**Status:** ACTIVE

## 🗺️ Executive Summary
The system has stabilized "Context Awareness" (History, Active Window) and "Reflexive Triggers". The `VideoSensor` is now running efficiently with "Eco Mode".
The focus for this week shifts to **"Intelligence & Tuning"**. We must reduce false positives (especially in "Meeting Mode") and ensure interventions are timely but not annoying (via Tiered Escalation). We also need to validate the "Voice Interface" reliability.

## 1. Change Summary (Last 7 Days)
*   **Merged**: **Context History**: `LogicEngine` now feeds a narrative of recent window switches to the LMM.
*   **Merged**: **Reflexive Triggers V2**: Immediate interventions for Games/Social Media based on window titles.
*   **Merged**: **VideoSensor Stabilization**: Fixed deadlock issues and implemented "Eco Mode" (skipping face detection during low motion).
*   **Verified**: **Replay Harness**: The harness is ready for tuning tasks.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: Tuning "Doom Scroll" Detection
*   **Goal**: Ensure the system correctly identifies "Doom Scrolling" without false positives during normal browsing.
*   **Deliverable**:
    1. `datasets/doom_scroll.json`: A synthetic dataset with realistic event sequences (phone usage, rapid switching).
    2. Tuned `DOOM_SCROLL_THRESHOLD` using `tools/replay_harness.py` to achieve >90% accuracy.
*   **Success Metric**: Passing test suite on `datasets/doom_scroll.json`.

### 🎯 Milestone 2: Intelligent Interventions (Tiered Policy)
*   **Goal**: Reduce "Alert Fatigue" by implementing a centralized escalation policy.
*   **Deliverable**:
    1. Refactor `LogicEngine` to route all interventions through `InterventionEngine`.
    2. Implement **Escalation Logic**: If a Tier 1 alert is ignored (or user persists), escalate to Tier 2 (Audible/Visual).
    3. Centralized Cooldowns: Move `reflexive_trigger_cooldown` logic into `InterventionEngine`.
*   **Success Metric**: System suppresses redundant alerts and correctly escalates persistent "bad" states.

### 🎯 Milestone 3: UX "Do Not Disturb" Controls
*   **Goal**: Allow users to instantly silence the bot without killing the process.
*   **Deliverable**:
    1. Verify Tray Icon menu items ("Snooze", "Do Not Disturb", "Quit").
    2. Ensure visual feedback (icon flashing) works for all intervention types.
*   **Success Metric**: Clicking "Snooze" in the tray immediately stops all interventions for the configured duration.

### 🎯 Milestone 4: Voice Command Reliability
*   **Goal**: Ensure "Take a picture" and other voice commands work consistently.
*   **Deliverable**:
    1. Add comprehensive tests for `STTInterface` command parsing.
    2. Verify `VOICE_COMMANDS` config integration in `LogicEngine`.
*   **Success Metric**: Voice commands trigger the correct intervention >95% of the time in quiet environments.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **Meeting Mode False Positives** | High | User watching YouTube looks like "Face + Speech". Mitigation: Require "User Input" (Keyboard/Mouse) or tune VAD thresholds. |
| **LMM Latency w/ History** | Med | Sending history increases token count/latency. Mitigation: Prune history string or summarize older entries. |
| **Privacy Redaction** | High | Is `[REDACTED]` enough? Mitigation: Add tests for "fuzzy" sensitive keywords. |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Create 'Doom Scroll' Dataset** | Tuning. | `datasets/doom_scroll.json` exists with labeled events. | S | Low | Testsmith |
| **Centralize Intervention Logic** | Arch. | `LogicEngine` delegates all cooldown/tier checks to `InterventionEngine`. | M | Med | Navigator |
| **Verify Tray Icon DND** | UX. | "Do Not Disturb" menu item correctly sets mode to `dnd`. | S | Low | Testsmith |
| **Test Voice Commands** | Reliability. | New test file `tests/test_voice_commands.py` verifies parsing. | S | Low | Testsmith |
| **Tune Meeting Mode VAD** | User Exp. | Adjust `VAD_STRONG_THRESHOLD` to reduce YouTube false positives. | M | Med | Calibrator |
| **Add 'Gaming Mode' Preset** | User Value. | Config preset that disables most interventions except "Posture". | S | Low | Sentinel |
| **Profile LMM Token Usage** | Perf. | Log token usage per request with History enabled. | S | Low | Profiler |
| **Refactor 'Eco Mode' Config** | Cleanliness. | Ensure `VIDEO_ECO_HEARTBEAT_INTERVAL` is documented in `CONFIGURATION.md`. | S | Low | Scribe |
| **Add 'Fuzzy Match' for Privacy** | Privacy. | Redaction catches typos of sensitive apps (e.g. "KeePass" vs "keepass"). | M | Low | Sentinel |
| **Implement 'Escalation Policy'** | UX. | Repeated triggers increase Intervention Tier. | L | High | Navigator |
