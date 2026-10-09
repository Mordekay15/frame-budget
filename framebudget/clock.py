"""Clocks: where the game loop gets "now" from, and how it waits.

RealClock uses the machine's monotonic clock and really sleeps. It is what you
use to show real tick durations and real overruns (Steps 1, 4, 5).

SimClock is a virtual clock. `now()` is a number we move forward ourselves:
waiting until a time just jumps to it, and "doing work that takes 200 ms" just
adds 200 ms. Nothing depends on how fast the computer is or on thread timing,
so a run with the same seed always produces exactly the same result. That is
what makes experiments repeatable (Step 6) and lets us run thousands of games
in minutes instead of days (Step 9).
"""

from __future__ import annotations

import time


class RealClock:
    # time.sleep can wake up a little late. We sleep until shortly before the
    # target and then spin on the clock for the last stretch, which gives a
    # precision of a few microseconds instead of up to a millisecond or more.
    SPIN_S = 0.002

    def now(self) -> float:
        return time.perf_counter()

    def sleep_until(self, t: float) -> None:
        while True:
            remaining = t - time.perf_counter()
            if remaining <= 0:
                return
            if remaining > self.SPIN_S:
                time.sleep(remaining - self.SPIN_S)

    def wait(self, seconds: float) -> None:
        """Block for `seconds` (used to model a blocking call)."""
        self.sleep_until(time.perf_counter() + seconds)


class SimClock:
    def __init__(self, start: float = 0.0):
        self.t = start

    def now(self) -> float:
        return self.t

    def sleep_until(self, t: float) -> None:
        if t > self.t:
            self.t = t

    def wait(self, seconds: float) -> None:
        self.t += seconds
