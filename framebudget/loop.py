"""A fixed-timestep loop.

Every tick is scheduled at an absolute time: tick i starts at start + i * dt.
Computing the schedule from the start time, instead of "now + dt" after each
tick, is what prevents drift: small sleep errors don't add up, because each
tick aims at its own fixed target.

If a tick's work takes longer than dt (an overrun), the next tick starts late,
immediately. The game still advances by exactly dt per tick (that is what
"fixed timestep" means), so game logic stays deterministic; the overrun shows
up in the log as lateness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

TICK_S = 0.033  # 33 ms, roughly 30 ticks per second


@dataclass
class TickRecord:
    i: int
    scheduled: float  # when the tick should have started (s since loop start)
    started: float  # when it actually started
    work: float  # how long the tick function ran (s)
    period: float  # time since the previous tick started (s); dt if all is well

    @property
    def lateness(self) -> float:
        return self.started - self.scheduled


def run_loop(
    tick: Callable[[int], bool | None],
    clock,
    n_ticks: int | None = None,
    dt: float = TICK_S,
) -> list[TickRecord]:
    """Run `tick(i)` every dt seconds until it returns True or n_ticks have run."""
    records: list[TickRecord] = []
    t0 = clock.now()
    prev_start = None
    i = 0
    while n_ticks is None or i < n_ticks:
        target = t0 + i * dt
        clock.sleep_until(target)
        start = clock.now()
        stop = tick(i)
        end = clock.now()
        period = dt if prev_start is None else start - prev_start
        records.append(TickRecord(i, target - t0, start - t0, end - start, period))
        prev_start = start
        i += 1
        if stop:
            break
    return records


def tick_summary(records: list[TickRecord], dt: float = TICK_S) -> dict:
    """Numbers that describe how well the loop kept its rhythm."""
    import statistics as st

    periods = sorted(r.period * 1000 for r in records[1:]) or [dt * 1000]
    late = [r.lateness * 1000 for r in records]

    def pct(xs, q):
        return xs[min(len(xs) - 1, int(q * len(xs)))]

    return {
        "ticks": len(records),
        "period_mean_ms": st.fmean(periods),
        "period_std_ms": st.pstdev(periods),
        "period_p50_ms": pct(periods, 0.50),
        "period_p99_ms": pct(periods, 0.99),
        "period_max_ms": periods[-1],
        "work_max_ms": max(r.work for r in records) * 1000,
        "lateness_max_ms": max(late),
        "final_drift_ms": late[-1],
        "overruns": sum(1 for r in records if r.work > dt),
        "blowout_factor": periods[-1] / (dt * 1000),
    }
