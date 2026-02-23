# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-02-26
**Status:** ACTIVE

## 🗺️ Executive Summary
The system has successfully stabilized "Intervention Logic" (Tiered Escalation, Centralized Cooldowns) and "User Controls" (Tray DND/Snooze). The "Doom Scroll" scenario is now verifiable via a synthetic dataset.
The focus for this week is **"Precision & Hardening"**. We must eliminate false positives in "Meeting Mode" (which triggers during video playback), harden privacy redaction against typos, and optimize LMM context usage.

## 1. Change Summary (Last 7 Days)
*   **Merged**: **Doom Scroll Scenario**: Validated `datasets/doom_scroll.json` with `tests/test_scenario_json.py` (100% accuracy).
*   **Merged**: **Centralized Interventions**: `InterventionEngine` now handles all cooldowns and escalations (Tier 1 -> Tier 2/3).
*   **Merged**: **UX Controls**: System Tray now supports "Snooze", "Do Not Disturb", and visual feedback.
*   **Verified**: **Voice Commands**: Confirmed reliability of "Take a picture" and other local voice triggers.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: Refine "Meeting Mode" (False Positive Reduction)
*   **Goal**: Prevent "Meeting Mode" (DND) from triggering when the user is simply watching YouTube or Netflix.
*   **Deliverable**:
    1. Implement a **Window Title Blacklist** for Meeting Mode (e.g., "YouTube", "Netflix", "VLC", "Twitch").
    2. If a blacklisted window is active, suppress "Meeting Mode" even if Face+Speech is detected.
*   **Success Metric**: `scenarios/test_meeting_mode.py` passes with a "Watching YouTube" scenario that *fails* to trigger Meeting Mode.

### 🎯 Milestone 2: Privacy Hardening (Fuzzy Matching)
*   **Goal**: Ensure sensitive window titles are redacted even if they contain typos or variations (e.g., "KePass" vs "KeePass").
*   **Deliverable**:
    1. Update `LogicEngine._scrub_window_title` to use fuzzy string matching (e.g., Levenshtein distance) or regex variations.
    2. Add `tests/test_privacy_fuzzy.py`.
*   **Success Metric**: "KePass XC" and "LastPass" (case insensitive) are redacted to `[REDACTED]`.

### 🎯 Milestone 3: LMM Context Optimization
*   **Goal**: Prevent "Context History" from bloating LMM prompts and increasing latency/cost.
*   **Deliverable**:
    1. Profile LMM token usage per request with `HISTORY_WINDOW_SIZE=5`.
    2. Implement "Context Summarization": If history > N tokens, summarize older entries into a single string.
*   **Success Metric**: LMM prompt size remains under 2000 tokens even after 1 hour of usage.

### 🎯 Milestone 4: "Gaming Mode" Preset
*   **Goal**: Provide a configuration profile for gamers that disables distractions but keeps posture checks.
*   **Deliverable**:
    1. Add `presets/gaming.json` (or similar config logic).
    2. Ensure "High Video Activity" (gameplay) does not trigger "Take a break" spam in this mode.
*   **Success Metric**: User can switch to "Gaming Mode" via Tray (or Config) and play a high-motion game without interruptions.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **Microphone vs System Audio** | High | Meeting Mode relies on "Speech". If system audio (YouTube) is heard as speech, it triggers false positives. Mitigation: Window Title Blacklist. |
| **LMM Context Window Limits** | Med | Long history + Vision tokens might hit model limits (8k/32k). Mitigation: Summarization or aggressive pruning. |
| **Fuzzy Match Performance** | Low | calculating Levenshtein distance on every frame might add CPU load. Mitigation: Only check on window switch events. |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Implement Meeting Mode Blacklist** | UX. | `LogicEngine` ignores Meeting Mode triggers if active window is in blacklist. | M | Med | Calibrator |
| **Add Fuzzy Privacy Matching** | Privacy. | `test_privacy_fuzzy.py` passes for "KePass" variations. | S | Low | Sentinel |
| **Profile LMM Token Usage** | Perf. | Logs show token count per request. | S | Low | Profiler |
| **Create 'Gaming Mode' Preset** | User Value. | Config preset exists and suppresses specific alerts. | S | Low | Navigator |
| **Tune VAD for System Audio** | Reliability. | Investigate if we can distinguish Mic vs System audio (Echo Cancellation?). | L | High | Calibrator |
| **Add 'Summarization' to History** | Perf. | Old history entries are replaced by a summary string. | M | Med | Scribe |
| **Verify Linux Wayland Support** | Compat. | Ensure new WindowSensor logic works on GNOME/KDE Wayland. | M | High | Testsmith |
| **Refactor Config to JSON/YAML** | Arch. | Move away from `config.py` to `config.json` for easier GUI editing. | L | Med | Navigator |
