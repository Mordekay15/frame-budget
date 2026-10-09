"""The decider interface: `decide(state) -> Answer`.

Anything that can make a difficulty decision sits behind this one method: the
hand-written rules, the real Jev, or a simulated Jev. The architectures (how and
when a decider is asked) are separate, in arch.py, so every architecture can be
combined with every decider.

An Answer is the decision plus what it cost: how long it took and how many
tokens it used. `ok=False` means there is no usable decision (error, timeout).

`real_time` tells the architecture whether the time was really spent. The live
Jev really blocks for its latency; a simulated Jev only reports a latency and
the architecture charges it to the clock (see `charge_latency`).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .clock import SimClock
from .decision import Decision, DecisionState, state_to_text
from .game import REGEN_PER_WAVE, expected_wave_damage
from .rules import LADDER, HunickePolicy


TIMEOUT_MS = 10_000.0  # the HTTP timeout of JevClient


@dataclass
class Answer:
    decision: Decision | None
    latency_ms: float
    ok: bool = True
    input_tokens: int = 0
    error: str = ""


class RuleDecider:
    """The Hunicke policy behind the decider interface. Instant."""

    real_time = False

    def __init__(self, policy: HunickePolicy | None = None):
        self.policy = policy or HunickePolicy()

    def decide(self, state: DecisionState) -> Answer:
        return Answer(self.policy.decide(state), 0.0)


class LiveJevDecider:
    """The real Jev, over the network. Blocks for as long as the request takes."""

    real_time = True

    def __init__(self, client):
        self.client = client

    def decide(self, state: DecisionState) -> Answer:
        r = self.client.decide(state_to_text(state))
        return Answer(r.decision, r.latency_ms, r.ok, r.input_tokens, r.error)

    def close(self) -> None:
        self.client.close()


class FakeAnswers:
    """What a simulated Jev answers. Offline stand-in for Jev's judgement.

    It aims for a wave whose damage keeps the player around 80% health: more
    damage when healthy, less when hurt. Overshooting the target damage counts
    three times as bad as undershooting it, a simple form of caution. Gumbel noise of strength `noise` makes
    it choose a neighbouring difficulty now and then, so that it is neither
    perfect nor perfectly consistent, like a real model. noise=0 makes it
    deterministic.
    """

    def __init__(self, seed: int = 0, noise: float = 0.3, target_health: float = 80.0,
                 overshoot: float = 3.0):
        self.rng = random.Random(seed)
        self.overshoot = overshoot
        self.noise = noise
        self.target_health = target_health

    def answer(self, state: DecisionState, text: str) -> tuple[Decision, int]:
        rate = state.last_count / state.last_clear_time if state.last_clear_time > 0 else 2.0
        target = REGEN_PER_WAVE + 0.4 * (state.health - self.target_health)
        scale = max(5.0, 0.3 * abs(target) + 5.0)
        best, best_score = None, -math.inf
        for c, m in LADDER:
            miss = expected_wave_damage(c, m, rate) - target
            score = -(miss * self.overshoot if miss > 0 else -miss) / scale
            if self.noise > 0:
                score += self.noise * -math.log(-math.log(self.rng.random() or 1e-12))
            if score > best_score:
                best, best_score = (c, m), score
        tokens = 180 + len(text) // 4  # close to what Jev reports for our requests
        return Decision(*best, source="jev"), tokens


class SimulatedJev:
    """A Jev made of an answer source (what) and a latency model (when)."""

    real_time = False

    def __init__(self, answers=None, latency=None):
        from .latency import LognormalLatency

        self.answers = answers or FakeAnswers()
        self.latency = latency or LognormalLatency()

    def decide(self, state: DecisionState) -> Answer:
        ms = self.latency.sample_ms()
        if math.isinf(ms):  # a request that failed in the recording: a timeout here
            return Answer(None, TIMEOUT_MS, False, 0, "timeout")
        text = state_to_text(state)
        decision, tokens = self.answers.answer(state, text)
        return Answer(decision, ms, True, tokens)


def charge_latency(clock, decider, latency_ms: float) -> None:
    """Make the clock show the time a blocking call took.

    The live Jev has already used up real time, so on the RealClock nothing more
    is needed. A simulated decider only reports a latency, and on the SimClock no
    real time counts anyway, so in those cases we wait (or jump) explicitly.
    """
    if isinstance(clock, SimClock) or not getattr(decider, "real_time", False):
        clock.wait(latency_ms / 1000)


