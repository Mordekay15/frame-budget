"""Step 7: state signatures for the decision cache.

A cache only helps if two states that deserve the same decision get the same
key. The signature throws away detail on purpose:

  health bucket      health rounded down to steps of 10 * c
  last wave size     the number of enemies in the wave just cleared (exact)
  damage trend       net health change of the last wave (damage minus regen),
                     in steps of 10 * c
  kill rate bucket   the player's kill rate in the last wave, in steps of 0.5 * c

`c` is the coarseness. At c = 1, health is "rounded to tens" as in the plan. Larger
c means fewer, bigger buckets: more cache hits, but more different situations
(and different players) share one decision. Smaller c means the opposite.
"""

from __future__ import annotations

import math

from .decision import DecisionState
from .game import REGEN_PER_WAVE


def wave_kill_rate(s: DecisionState) -> float:
    return s.last_count / s.last_clear_time if s.last_clear_time > 0 else s.kill_rate


def signature(s: DecisionState, coarse: float = 1.0) -> tuple:
    trend = s.last_wave_damage - REGEN_PER_WAVE
    return (
        int(s.health // (10 * coarse)),
        s.last_count,
        math.floor(trend / (10 * coarse)),
        int(wave_kill_rate(s) // (0.5 * coarse)),
    )
