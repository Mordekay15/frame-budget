"""A stand-in for Jev that needs no network and no API key.

It answers with a simple, slightly noisy heuristic and reports a latency drawn
from a latency model. It exists so the code can be developed and tested offline;
results that go into the thesis must come from the real Jev.
"""

from __future__ import annotations

import random
import time

from .decision import DAMAGE_MULTS, ENEMY_COUNTS, Decision
from .jev import COUNT_KEYS, MULT_KEYS, JevResult
from .latency import LognormalLatency

_COUNT_KEY = {v: k for k, v in COUNT_KEYS.items()}
_MULT_KEY = {v: k for k, v in MULT_KEYS.items()}


def heuristic_answer(health_frac: float, wave_damage_frac: float, rng: random.Random) -> Decision:
    """Harder when the player is healthy and barely hurt, easier when in danger."""
    # 0 = easiest, 1 = hardest
    target = health_frac - 1.5 * wave_damage_frac + rng.gauss(0, 0.1)
    target = min(max(target, 0.0), 0.999)
    count = ENEMY_COUNTS[int(target * len(ENEMY_COUNTS))]
    mult = DAMAGE_MULTS[int(min(max(target + rng.gauss(0, 0.1), 0), 0.999) * len(DAMAGE_MULTS))]
    return Decision(count, mult, source="jev")


class FakeJevClient:
    """Same `decide()` interface as JevClient."""

    def __init__(self, latency=None, seed: int = 0, sleep: bool = False):
        self.latency = latency or LognormalLatency(seed=seed)
        self.rng = random.Random(seed + 1)
        self.sleep = sleep

    def decide(self, state_text: str, fresh_connection: bool = False) -> JevResult:
        ms = self.latency.sample_ms() + (60.0 if fresh_connection else 0.0)
        if self.sleep:
            time.sleep(ms / 1000)
        # Pull the two numbers the heuristic needs back out of the text.
        health = _number_after(state_text, "Player health: ") / 100
        damage = _number_after(state_text, "The player took ") / 100
        d = heuristic_answer(health, damage, self.rng)
        probs = {k: (0.7 if v == d.count else 0.1) for k, v in COUNT_KEYS.items()}
        mprobs = {k: (0.7 if v == d.mult else 0.1) for k, v in MULT_KEYS.items()}
        tokens = 180 + len(state_text) // 4
        return JevResult(
            ms, True, 200, decision=d, count_confidence=0.7, mult_confidence=0.7,
            count_probs=probs, mult_probs=mprobs, input_tokens=tokens,
            cost=tokens * 0.042 / 1e6, served_model="fake-jev", provider="offline",
        )

    def close(self) -> None:
        pass


def _number_after(text: str, marker: str) -> float:
    i = text.find(marker)
    if i < 0:
        return 0.0
    j = i + len(marker)
    k = j
    while k < len(text) and (text[k].isdigit() or text[k] == "."):
        k += 1
    return float(text[j:k] or 0)
