# ASDGPT Weekly Roadmap Refresh



**Date:** 2026-03-08
**Status:** ACTIVE

## 🗺️ Executive Summary
The system has successfully stabilized **"Performance & Limits"** with the implementation of LMM Context Summarization, preventing context history from bloating beyond token limits. We also identified and resolved a critical resource leak in the video sensor, improving long-term reliability.
The focus for this week shifts to **"Reliability & Fallbacks"**. We must ensure the system gracefully degrades during LMM outages (Offline Fallback), introduce dedicated user UX modes (like "Gaming Mode"), and migrate our configuration to JSON/YAML to support future GUI configuration tools.

## 1. Change Summary (Last 7 Days)
*   **Merged**: **LMM Context Summarization**: Context history is now compressed dynamically, preventing token bloat and preserving LMM prompt latency over long sessions.
*   **Merged**: **Reliability Hardening**: Resolved a major `cv2.VideoWriter` resource leak in `_record_video` that was causing memory and file descriptor issues.
*   **Merged**: **Doc Improvements**: `MODES.md` was added and `CONFIGURATION.md` was updated with hotkey and verification steps.
*   **Cleanup**: Finalized branch verification and closed out stale PRs, improving repository hygiene.

## 2. Top Milestones (Next 7 Days)

### 🎯 Milestone 1: LMM Offline Fallback & Reliability Hardening
*   **Goal**: Ensure the system does not crash or hang when the local LLM server (e.g., LM Studio/Ollama) goes offline or times out.
*   **Deliverable**:
    1. Harden `LMMInterface` against connection timeouts.
    2. Implement a robust "Offline Fallback" where reflexive triggers (Window title rules) and basic timers continue to operate even if the LMM is unreachable.
*   **Success Metric**: If the LLM server is killed mid-session, ASDGPT continues running and can trigger a "distraction alert" based solely on `config.DISTRACTION_APPS`.




### 🎯 Milestone 2: "Gaming Mode" Preset
*   **Goal**: Provide a configuration profile for gamers that disables distractions and non-critical interventions, but optionally keeps posture checks.
*   **Deliverable**:
    1. Add `presets/gaming.json` (or dynamic mode switching via System Tray).
    2. Ensure "High Video Activity" (gameplay) and game window titles do not trigger "Take a break" spam.
*   **Success Metric**: User can switch to "Gaming Mode" via Tray and play a high-motion game for 2 hours without low-tier interruptions.



### 🎯 Milestone 3: Refactor Configuration to JSON
*   **Goal**: Move away from a pure Python `config.py` file to a standard `config.json` format to enable future GUI editors.
*   **Deliverable**:
    1. Port all constants from `config.py` into a robust JSON schema.
    2. Update `_get_conf` logic to handle schema defaults seamlessly.
*   **Success Metric**: Users can edit `config.json` without touching Python code, and the application reloads gracefully.

### 🎯 Milestone 4: Tune VAD for System Audio Discrimination
*   **Goal**: Ensure the voice activity detector (VAD) is not triggered by system audio output.
*   **Deliverable**:
    1. Investigate and implement basic echo cancellation or strict input device filtering.
*   **Success Metric**: High-volume output from speakers does not trigger "speech_detected" when the user is silent.




## 3. De-risk List (Unknowns)

| Unknown | Impact | Mitigation |
| :--- | :--- | :--- |


| **Fallback Reflex Tuning** | Med | If LMM is offline, reflexive rules might be too aggressive or miss context. Mitigation: Ensure reflexive cooldowns are strict (e.g., 5 mins minimum) and prioritize high-confidence rules. |
| **GUI Presets Switching** | Low | Swapping entire configs at runtime could cause race conditions in sensor threads. Mitigation: Restart the engine or selectively reload safe variables with proper thread locks. |
| **System Audio Interference** | High | Current PyAudio setup might be listening to a 'Stereo Mix' or loopback. Mitigation: Add explicit device selection or basic spectral filtering to distinguish mic vs output. |




## 4. Backlog (Selected High Priority)

| Title | Why | Acceptance Criteria | Estimate | Risk | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |

| **Harden LMM Timeout & Offline Fallback** | Reliability. | System survives LLM server crash and uses local rules. | M | Med | Calibrator |
| **Create 'Gaming Mode' Preset** | User Value. | Config preset exists and suppresses specific alerts. | S | Low | Navigator |


| **Refactor Config to JSON** | Arch. | Move away from `config.py` to `config.json` for easier GUI editing. | L | Med | Navigator |
| **Tune VAD for System Audio** | Reliability. | Investigate if we can distinguish Mic vs System audio (Echo Cancellation?). | L | High | Calibrator |
| **Add "Focus Mode" Timer** | UX. | User can trigger a Pomodoro-style block via tray. | M | Low | Sentinel |
| **Verify Linux Wayland Support** | Compat. | Ensure new WindowSensor logic works on GNOME/KDE Wayland. | M | High | Testsmith |
| **Expand Voice Command Set** | UX. | Add commands for "Pause", "Resume", "Report status". | S | Low | Navigator |
| **Create Dashboard UI Prototype** | UX. | Initial web or local dashboard to view timeline/metrics. | L | High | Scribe |
