# ASDGPT Modes

ASDGPT uses different operational modes to control monitoring behavior and intervention frequency. This ensures the system can be active when needed, but stay out of your way during meetings, deep focus, or when you explicitly request a break.

## Mode Definitions

### 1. Active Mode
*   **What it does**: This is the default, fully operational state.
*   **Behavior**:
    *   **Monitoring**: Sensors (audio, video, active window) are continuously polling.
    *   **LMM Analysis**: Triggered normally based on events (e.g., loud audio, high motion) or periodic heartbeats.
    *   **Interventions**: Allowed and actively executed based on triggers and LMM suggestions.

### 2. Snoozed Mode
*   **What it does**: A temporary state to suppress interventions without entirely blinding the system.
*   **Behavior**:
    *   **Monitoring**: "Light monitoring without intervention." Sensor data is still processed.
    *   **LMM Analysis**: Called periodically to keep context up to date.
    *   **Interventions**: Suppressed (`allow_intervention=False`).
    *   **Transitions**: Automatically returns to `active` mode after the snooze duration expires.

### 3. Paused Mode
*   **What it does**: Completely halts interventions and largely suspends logic engine updates.
*   **Behavior**:
    *   **Monitoring**: While sensor threads may still run in the background, the logic engine ignores the data.
    *   **LMM Analysis**: Skipped.
    *   **Interventions**: Suppressed.
    *   **Transitions**: Activated by toggling pause/resume. When toggled off, it returns to the mode it was in before pausing (e.g., if you paused while snoozed, you return to snoozed). If the snooze duration expired while paused, it will resume in `active` mode.

### 4. DND (Meeting Mode)
*   **What it does**: An implicit "Do Not Disturb" state, automatically triggered by heuristics to prevent the system from interrupting you during a meeting.
*   **Behavior**:
    *   **Trigger**: Activated automatically when continuous speech is detected for a certain duration *alongside* no keyboard activity for a certain duration.
    *   **Interventions**: Suppressed.
    *   **Transitions**: Exits Meeting Mode (Auto-DND) and returns to `active` as soon as user keyboard/mouse activity is detected.

## How to Verify

1.  **Verify Meeting Mode (Auto-DND)**:
    *   Run the application (`python main.py`).
    *   Speak continuously into your microphone.
    *   Do **not** touch your keyboard or mouse for at least 10 seconds.
    *   Watch the console logs or tray icon; you should see it switch to DND / Meeting Mode.
    *   Touch your keyboard or mouse to verify it switches back to `active`.
2.  **Verify Pause/Resume**:
    *   Use the toggle pause/resume functionality.
    *   Observe the logs to confirm the mode changes to `paused`.
    *   Toggle again to confirm it returns to the previous state.
