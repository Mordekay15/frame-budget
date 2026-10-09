"""The rule-based baseline: Hunicke's "comfort zone" policy.

Hunicke and Chapman's Hamlet system (Half-Life) watches the damage the player
takes, models it as a normal distribution, and from that estimates the
probability that the player dies in the near future. When that probability
crosses a threshold (40% in the comfort policy) the system intervenes.

  Hunicke, R., Chapman, V. (2004). AI for Dynamic Difficulty Adjustment in Games.
  AAAI Workshop on Challenges in Game AI.
  Hunicke, R. (2005). The case for dynamic difficulty adjustment in games. ACE '05.

Our version, at every decision point:
  1. Estimate the player's kill rate from recent waves (count / clear time).
  2. For any candidate difficulty, the expected damage of the next wave is
     BASE_DPS * mult * n(n+1)/2 / kill_rate (see game.py). Its spread comes from
     how far real waves have deviated from that expectation so far.
  3. P(death) = P(damage over the next few waves, minus regeneration, exceeds
     current health), from the normal distribution. Hamlet also predicted over
     a short time window rather than a single hit.
  4. If P(death) at the current difficulty is above 40%, step down the
     difficulty ladder until it isn't (Hunicke's intervention).
     If the player is bored (health at or above 90%, the same line the
     `bored` metric uses) and even one step up keeps P(death) below 10%,
     step up one level: the player is outside the comfort zone on the boring side. This upper bound
     is our symmetric extension; Hamlet mainly intervened to help.

The policy only looks at DecisionState, so it can serve as Jev's fallback.
"""

from __future__ import annotations

import math
import statistics

from .decision import DAMAGE_MULTS, ENEMY_COUNTS, Decision, DecisionState
from .game import DEFAULT_DECISION, REGEN_PER_WAVE, expected_wave_damage, normal_cdf

# All 16 difficulties, ordered from the easiest to the hardest by expected damage.
LADDER: list[tuple[int, float]] = sorted(
    ((c, m) for c in ENEMY_COUNTS for m in DAMAGE_MULTS),
    key=lambda cm: (cm[0] * (cm[0] + 1) * cm[1], cm[0]),
)


class HunickePolicy:
    def __init__(self, death_threshold: float = 0.40, boredom_threshold: float = 0.10,
                 min_rel_std: float = 0.25, bored_health: float = 0.9, horizon: int = 4):
        self.death_threshold = death_threshold
        self.boredom_threshold = boredom_threshold
        self.min_rel_std = min_rel_std
        self.horizon = horizon
        self.bored_health = bored_health
        self.level = LADDER.index(DEFAULT_DECISION.key())
        self._rates: list[float] = []
        self._ratios: list[float] = []  # actual / expected damage of past waves

    def observe(self, s: DecisionState) -> None:
        """Update the statistics with the wave that was just cleared."""
        if s.last_count <= 0 or s.last_clear_time <= 0:
            return
        rate = s.last_count / s.last_clear_time
        self._rates.append(rate)
        expected = expected_wave_damage(s.last_count, s.last_mult, self.kill_rate())
        if expected > 0:
            self._ratios.append(s.last_wave_damage / expected)

    def kill_rate(self) -> float:
        recent = self._rates[-5:]
        return statistics.fmean(recent) if recent else 2.0

    def p_death(self, health: float, count: int, mult: float) -> float:
        """P(the player dies within the next `horizon` waves at this difficulty).

        Over H waves the player takes H wave-damages and regains H-1 regens (death
        can happen before the last regen). Wave damages are treated as independent,
        so the mean adds up H times and the standard deviation sqrt(H) times.
        """
        mu1 = expected_wave_damage(count, mult, self.kill_rate())
        ratios = self._ratios[-10:]
        bias = statistics.fmean(ratios) if ratios else 1.0
        rel = statistics.pstdev(ratios) if len(ratios) >= 3 else 0.0
        mu1 *= bias
        sigma1 = max(rel, self.min_rel_std) * mu1
        h = self.horizon
        mu = h * mu1 - (h - 1) * REGEN_PER_WAVE
        sigma = sigma1 * math.sqrt(h)
        if sigma <= 0:
            return 0.0 if health > mu else 1.0
        return 1.0 - normal_cdf((health - mu) / sigma)

    def decide(self, s: DecisionState) -> Decision:
        """Observe the state, then pick the next wave's difficulty."""
        self.observe(s)
        lvl = self.level
        while lvl > 0 and self.p_death(s.health, *LADDER[lvl]) > self.death_threshold:
            lvl -= 1
        bored = s.health >= self.bored_health * s.max_health
        if bored and lvl == self.level and lvl + 1 < len(LADDER):
            if self.p_death(s.health, *LADDER[lvl + 1]) < self.boredom_threshold:
                lvl += 1
        self.level = lvl
        return Decision(*LADDER[lvl], source="rules")

    def peek(self, s: DecisionState) -> Decision:
        """What decide() would answer, without changing any state (used by prefetch)."""
        saved = (self.level, list(self._rates), list(self._ratios))
        try:
            return self.decide(s)
        finally:
            self.level, self._rates, self._ratios = saved


def p_death_from_state(s: DecisionState, count: int, mult: float, rel_std: float = 0.3) -> float:
    """A stateless version of the estimate, used to label states (cache, analysis)."""
    rate = s.last_count / s.last_clear_time if s.last_clear_time > 0 else max(s.kill_rate, 0.5)
    mu = expected_wave_damage(count, mult, rate)
    return 1.0 - normal_cdf((s.health - mu) / max(rel_std * mu, 1e-9))


