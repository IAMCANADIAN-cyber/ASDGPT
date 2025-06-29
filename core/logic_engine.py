import time
import config

class LogicEngine:
    def __init__(self):
        self.current_mode = config.DEFAULT_MODE
        self.snooze_end_time = 0
        self.previous_mode_before_pause = config.DEFAULT_MODE
        self.tray_callback = None # Callback for notifying tray/main app
        print(f"LogicEngine initialized. Mode: {self.current_mode}")

    def get_mode(self):
        old_mode = self.current_mode
        if self.current_mode == "snoozed":
            if time.time() >= self.snooze_end_time and self.snooze_end_time != 0:
                print("Snooze expired.")
                self.snooze_end_time = 0 # Reset snooze time
                self.set_mode("active", from_snooze_expiry=True)
                # set_mode will call _notify_mode_change

        # If mode was changed by snooze expiry, self.current_mode is now updated.
        # If not, it's the same as old_mode.
        return self.current_mode

    def set_mode(self, mode, from_snooze_expiry=False):
        if mode not in ["active", "snoozed", "paused", "error"]: # Added error mode
            print(f"Warning: Attempted to set invalid mode: {mode}")
            return

        old_mode = self.current_mode
        if mode == old_mode and not from_snooze_expiry : # Allow re-setting active if snooze expired
            # (e.g. if already active, but snooze expired, we still want notification)
            # This condition might need refinement based on desired notification behavior
            if not (mode == "active" and from_snooze_expiry and old_mode == "snoozed"):
                 return


        print(f"LogicEngine: Changing mode from {old_mode} to {mode}")

        if old_mode != "paused" and mode == "paused":
            self.previous_mode_before_pause = old_mode

        self.current_mode = mode

        if self.current_mode == "snoozed":
            self.snooze_end_time = time.time() + config.SNOOZE_DURATION
            print(f"Snooze activated. Will return to active mode in {config.SNOOZE_DURATION / 60:.0f} minutes.")
        elif self.current_mode == "active":
            # If mode becomes active (either by user or snooze expiry), ensure snooze_end_time is cleared
            self.snooze_end_time = 0

        self._notify_mode_change(old_mode, new_mode=self.current_mode, from_snooze_expiry=from_snooze_expiry)

    def cycle_mode(self):
        current_actual_mode = self.get_mode()
        if current_actual_mode == "active":
            self.set_mode("snoozed")
        elif current_actual_mode == "snoozed":
            self.set_mode("paused")
        elif current_actual_mode == "paused":
            # When cycling from paused, go to active, not previous_mode_before_pause
            self.set_mode("active")

    def toggle_pause_resume(self):
        current_actual_mode = self.get_mode()
        if current_actual_mode == "paused":
            # If snooze would have expired while paused, return to active.
            if self.previous_mode_before_pause == "snoozed" and \
               self.snooze_end_time != 0 and time.time() >= self.snooze_end_time:
                self.snooze_end_time = 0 # Clear snooze as it's now handled
                self.set_mode("active")
            else:
                self.set_mode(self.previous_mode_before_pause)
        else:
            # This will set self.previous_mode_before_pause correctly if current is not "paused"
            self.set_mode("paused")

    def _notify_mode_change(self, old_mode, new_mode, from_snooze_expiry=False):
        print(f"LogicEngine Notification: Mode changed from {old_mode} to {new_mode}")
        if self.tray_callback:
            # Pass both old and new mode for more context if needed by callback
            self.tray_callback(new_mode=new_mode, old_mode=old_mode)

if __name__ == '__main__':
    engine = LogicEngine()

    # Mock callback for testing
    def test_callback(new_mode, old_mode):
        print(f"Test Callback: Mode changed from {old_mode} to {new_mode}")
    engine.tray_callback = test_callback

    print(f"Initial mode: {engine.get_mode()}") # active

    engine.cycle_mode() # active -> snoozed
    print(f"Mode after cycle 1: {engine.get_mode()}") # snoozed

    engine.toggle_pause_resume() # snoozed -> paused
    print(f"Mode after pause: {engine.get_mode()}") # paused

    engine.toggle_pause_resume() # paused -> snoozed (restores previous_mode_before_pause)
    print(f"Mode after resume: {engine.get_mode()}") # snoozed

    print("\nSimulating snooze duration passing...")
    engine.snooze_end_time = time.time() - 1 # Force snooze to expire
    # get_mode() will trigger the change and notification
    print(f"Mode after snooze expired (on next get_mode call): {engine.get_mode()}")
    assert engine.current_mode == "active"

    print("\nTesting pause then snooze expiry while paused then resume...")
    engine.set_mode("active") # Reset to active
    engine.set_mode("snoozed") # snoozed
    engine.snooze_end_time = time.time() + 5 # Snooze for 5 seconds
    print(f"Snoozing for 5s. Current mode: {engine.get_mode()}")
    engine.set_mode("paused") # paused (while snoozing)
    print(f"Paused. Current mode: {engine.get_mode()}")
    print("Waiting for 6 seconds to ensure snooze expires...")
    time.sleep(6)
    # Snooze has now expired. previous_mode_before_pause is "snoozed".
    # snooze_end_time is in the past.
    engine.toggle_pause_resume() # paused -> active (because snooze expired)
    print(f"Mode after resuming from pause (snooze should have expired): {engine.get_mode()}")
    assert engine.current_mode == "active"

    engine.set_mode("active")
    engine.cycle_mode() # active -> snoozed
    engine.cycle_mode() # snoozed -> paused
    engine.cycle_mode() # paused -> active
    print(f"Mode after 3 cycles: {engine.get_mode()}")
    assert engine.current_mode == "active"
    print("LogicEngine tests complete.")
