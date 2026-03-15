# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-03-15
**Status:** ACTIVE

## 🗺️ Executive Summary
The system has successfully stabilized **"Precision & Hardening"** (Meeting Mode Blacklist, Fuzzy Privacy Matching, Centralized Escalation). The false positives during video playback (YouTube/Netflix) have been effectively mitigated, and privacy redactions are robust against typos.
The focus for this week shifts to **"Performance & UX Presets"**. We must prevent Local Multimodal Model (LMM) context bloat to ensure low latency, create a dedicated "Gaming Mode" preset, and harden the core logic against LMM timeouts or offline scenarios. Several PRs and branches are in flight for these features, but they must be merged into the main branch.

## 1. Change Summary (Last 7 Days)
*   **Merged**: Minor doc improvements and missing LogicEngine features resolved.
*   **In-flight (Open PRs/Branches)**:
    *   **Gaming Mode Preset**: Branches exist to provide a configuration profile for gamers that disables distractions and non-critical interventions.
    *   **Offline Fallback**: Branches exist to harden LogicEngine against LMM timeouts and offline scenarios.
    *   **LMM Context Summarization**: Branches exist to prevent "Context History" from bloating LMM prompts.
*   **Reverted**: None.
*   **Recurring pain points**: The gap between branches and `HEAD` is growing. Features are being developed in isolated branches but not merged, leading to fragmented progress and potential merge conflicts.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: Merge In-Flight Performance & UX Features
*   **Goal**: Consolidate "Gaming Mode", "Offline Fallback", and "LMM Context Summarization" from their respective branches into `HEAD`.
*   **Deliverable**:
    1. Resolve any merge conflicts for these features.
    2. Ensure unit tests pass for all features when combined.
*   **Success Metric**: `HEAD` includes working implementations of Gaming Mode, Offline Fallback, and Context Summarization.

### 🎯 Milestone 2: Refactor Configuration to JSON/YAML
*   **Goal**: Move away from a pure Python `config.py` file to a standard `config.json` or `config.yaml` format to enable future GUI editors.
*   **Deliverable**:
    1. Port all constants from `config.py` into a robust JSON schema or YAML file.
    2. Update `_get_conf` logic to handle schema defaults seamlessly.
*   **Success Metric**: Users can edit `config.json` without touching Python code, and the application reloads gracefully.

### 🎯 Milestone 3: UI Dashboard Prototype
*   **Goal**: Provide a local dashboard to view timeline and metrics.
*   **Deliverable**:
    1. Initial web or local dashboard to view timeline/metrics.
*   **Success Metric**: User can launch a dashboard to view the generated timeline events.

### 🎯 Milestone 4: Tune VAD for System Audio
*   **Goal**: Distinguish between Mic and System audio to prevent false triggers.
*   **Deliverable**:
    1. Investigate and implement Echo Cancellation or system audio filtering.
*   **Success Metric**: System audio (e.g., from videos) does not trigger Voice Activity Detection (VAD).

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **Merge Conflicts from Isolated Branches** | High | The longer branches stay unmerged, the higher the risk of severe conflicts, especially in `LogicEngine` and `InterventionEngine`. Mitigation: Prioritize merging existing features before building new ones. |
| **GUI Presets Switching** | Low | Swapping entire configs at runtime could cause race conditions in sensor threads. Mitigation: Restart the engine or selectively reload safe variables. |
| **Fallback Reflex Tuning** | Med | If LMM is offline, reflexive rules might be too aggressive. Mitigation: Ensure reflexive cooldowns are strict (e.g., 5 mins minimum). |
| **System Audio Capture Compatibility** | High | Capturing system audio to filter it from VAD can be OS-dependent and complex. Mitigation: Research cross-platform libraries like `soundcard` or focus on Windows/Linux specific implementations first. |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Merge 'Gaming Mode' Preset** | User Value | Gaming config preset exists and suppresses specific alerts. | S | Low | Navigator |
| **Merge LMM Timeout & Offline Fallback** | Reliability | System survives LLM server crash and uses local rules. | M | Med | Calibrator |
| **Merge LMM Context Summarization** | Perf | Old history entries are replaced by a summary string to keep token counts < 2000. | M | Med | Scribe |
| **Refactor Config to JSON** | Arch | Move away from `config.py` to `config.json` for easier GUI editing. | L | Med | Navigator |
| **Tune VAD for System Audio** | Reliability | Investigate if we can distinguish Mic vs System audio (Echo Cancellation?). | L | High | Calibrator |
| **Create Dashboard UI Prototype** | UX | Initial web or local dashboard to view timeline/metrics. | L | High | Scribe |
| **Add "Focus Mode" Timer** | UX | User can trigger a Pomodoro-style block via tray. | M | Low | Sentinel |
| **Verify Linux Wayland Support** | Compat | Ensure new WindowSensor logic works on GNOME/KDE Wayland. | M | High | Testsmith |
| **Expand Voice Command Set** | UX | Add commands for "Pause", "Resume", "Report status". | S | Low | Navigator |
| **Implement UI Presets Hot-Reloading** | UX | Ensure that mode switches via the Tray icon apply config defaults without a full app restart. | M | Med | Calibrator |
| **Consolidate Privacy Scrubber Rules** | Security | Move all regex filtering and title redactions into a centralized yaml list. | M | Low | Sentinel |
| **Create End-to-End Stress Test** | Quality | Generate a simulated full 8-hour workflow to trace memory and handle long-running resource management. | L | High | Testsmith |
