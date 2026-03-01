# Scribe Journal

## Run: Meeting Mode Docs
- "Meeting Mode" is an implicit state (Auto-DND) driven by `LogicEngine` heuristics, not an explicit user-settable mode.
- Users verify this by simulating a meeting (speech + presence) while idle on inputs.

## Run: Modes Documentation
- The system modes (Active, Snoozed, Paused, and DND) are explicitly defined.
- "Active", "Snoozed", and "Paused" are explicit states driven by the user (hotkeys) or timer logic (`snooze_end_time`), whereas "Meeting Mode" (DND) is dynamically and implicitly driven by heuristics.
- Snoozed mode performs "light monitoring without intervention" (`allow_intervention=False`).
- Paused mode skips sensor updates in the main LogicEngine loop.
