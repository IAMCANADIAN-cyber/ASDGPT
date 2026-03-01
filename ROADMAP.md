# ASDGPT Weekly Roadmap Refresh

**Date:** 2026-03-05
**Status:** ACTIVE

## 🗺️ Executive Summary
The system has successfully stabilized **"Precision & Hardening"** (Meeting Mode Blacklist, Fuzzy Privacy Matching, Centralized Escalation). The false positives during video playback (YouTube/Netflix) have been effectively mitigated, and privacy redactions are robust against typos.
The focus for this week shifts to **"Performance & UX Presets"**. We must prevent Local Multimodal Model (LMM) context bloat to ensure low latency, create a dedicated "Gaming Mode" preset, and harden the core logic against LMM timeouts or offline scenarios.

## 1. Change Summary (Last 7 Days)
*   **Merged**: **Meeting Mode Blacklist**: Suppresses auto-DND mode when passive media (YouTube, Netflix, VLC) is the active window, resolving false positives.
*   **Merged**: **Privacy Hardening**: Implemented fuzzy string matching for sensitive window titles (e.g., catching "KePass" alongside "KeePass").
*   **Merged**: **Centralized Escalation**: `InterventionEngine` now handles monotonic escalation (Tier 1 -> Tier 2 -> Tier 3 Visual Alerts) and implements a spam protection "Nag Interval".
*   **Architecture**: `LogicEngine` dependency on raw window strings was updated to ensure privacy redaction occurs upstream in `WindowSensor`.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: LMM Context Optimization (Summarization)
*   **Goal**: Prevent "Context History" from bloating LMM prompts, increasing latency, or hitting the 8k context limit.
*   **Deliverable**:
    1. Profile LMM token usage per request with `HISTORY_WINDOW_SIZE=5`.
    2. Implement "Context Summarization": If history > N tokens, summarize older entries into a single string.
*   **Success Metric**: LMM prompt size remains consistently under 2000 tokens even after 1 hour of continuous usage.

### 🎯 Milestone 2: "Gaming Mode" Preset
*   **Goal**: Provide a configuration profile for gamers that disables distractions and non-critical interventions, but optionally keeps posture checks.
*   **Deliverable**:
    1. Add `presets/gaming.json` (or dynamic mode switching via System Tray).
    2. Ensure "High Video Activity" (gameplay) and game window titles do not trigger "Take a break" spam.
*   **Success Metric**: User can switch to "Gaming Mode" via Tray and play a high-motion game for 2 hours without low-tier interruptions.

### 🎯 Milestone 3: LMM Offline Fallback & Reliability Hardening
*   **Goal**: Ensure the system does not crash or hang when the local LLM server (e.g., LM Studio/Ollama) goes offline or times out.
*   **Deliverable**:
    1. Harden `LMMInterface` against connection timeouts.
    2. Implement a robust "Offline Fallback" where reflexive triggers (Window title rules) and basic timers continue to operate even if the LMM is unreachable.
*   **Success Metric**: If the LLM server is killed mid-session, ASDGPT continues running and can trigger a "distraction alert" based solely on `config.DISTRACTION_APPS`.

### 🎯 Milestone 4: Refactor Configuration to JSON/YAML
*   **Goal**: Move away from a pure Python `config.py` file to a standard `config.json` or `config.yaml` format to enable future GUI editors.
*   **Deliverable**:
    1. Port all constants from `config.py` into a robust JSON schema or YAML file.
    2. Update `_get_conf` logic to handle schema defaults seamlessly.
*   **Success Metric**: Users can edit `config.json` without touching Python code, and the application reloads gracefully.

## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |
| **LMM Summarization Accuracy** | Med | Summarizing context might drop crucial temporal details needed by the "Mental Model" prompt. Mitigation: Test summary quality before rolling out. |
| **GUI Presets Switching** | Low | Swapping entire configs at runtime could cause race conditions in sensor threads. Mitigation: Restart the engine or selectively reload safe variables. |
| **Fallback Reflex Tuning** | Med | If LMM is offline, reflexive rules might be too aggressive. Mitigation: Ensure reflexive cooldowns are strict (e.g., 5 mins minimum). |

## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Implement LMM Context Summarization** | Perf. | Old history entries are replaced by a summary string to keep token counts < 2000. | M | Med | Scribe |
| **Create 'Gaming Mode' Preset** | User Value. | Config preset exists and suppresses specific alerts. | S | Low | Navigator |
| **Harden LMM Timeout & Offline Fallback** | Reliability. | System survives LLM server crash and uses local rules. | M | Med | Calibrator |
| **Profile LMM Token Usage** | Perf. | Logs show token count and prompt size per request. | S | Low | Profiler |
| **Refactor Config to JSON** | Arch. | Move away from `config.py` to `config.json` for easier GUI editing. | L | Med | Navigator |
| **Tune VAD for System Audio** | Reliability. | Investigate if we can distinguish Mic vs System audio (Echo Cancellation?). | L | High | Calibrator |
| **Add "Focus Mode" Timer** | UX. | User can trigger a Pomodoro-style block via tray. | M | Low | Sentinel |
| **Verify Linux Wayland Support** | Compat. | Ensure new WindowSensor logic works on GNOME/KDE Wayland. | M | High | Testsmith |
| **Expand Voice Command Set** | UX. | Add commands for "Pause", "Resume", "Report status". | S | Low | Navigator |
| **Create Dashboard UI Prototype** | UX. | Initial web or local dashboard to view timeline/metrics. | L | High | Scribe |
