import time
import cProfile
import pstats
import io
import threading

class Profiler:
    """
    Simple profiler for the main loop.
    """
    def __init__(self, logger):
        self.logger = logger
        self.profiler = cProfile.Profile()
        self.is_profiling = False

    def start(self):
        if not self.is_profiling:
            self.is_profiling = True
            self.profiler.enable()
            self.logger.log_info("Profiler started.")

    def stop(self):
        if self.is_profiling:
            self.is_profiling = False
            self.profiler.disable()
            s = io.StringIO()
            ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(20) # Top 20 lines
            self.logger.log_info(f"Profiler Results:\n{s.getvalue()}")

# To be integrated into main.py if desired via config/hotkey
