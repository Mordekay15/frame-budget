"""Architectures: who decides the next wave's difficulty, and when.

Step 3: RulesOnly, the baseline.
Step 4: Blocking, the loop waits for the decider.
"""

from __future__ import annotations

from .deciders import charge_latency
from .rules import HunickePolicy
from .sim import DecisionEvent


class RulesOnly:
    """Step 3: Hunicke's comfort-zone policy decides every wave, instantly."""

    name = "rules"

    def __init__(self):
        self.policy = HunickePolicy()
        self.events: list[DecisionEvent] = []

    def on_tick(self, game, clock) -> None:
        pass

    def on_decision_point(self, game, state, clock) -> None:
        d = self.policy.decide(state)
        game.next_decision = d
        self.events.append(DecisionEvent(game.wave + 1, clock.now(), applied=d))


class Blocking:
    """Step 4: ask the decider and wait for the answer, inside the tick.

    Deliberately bad. While the request is in flight nothing else happens: no
    tick, no game update, no rendering. The tick that hits a decision point lasts
    as long as the request. If the request fails, the rules decide.
    """

    name = "blocking"

    def __init__(self, decider):
        self.decider = decider
        self.rules = HunickePolicy()
        self.events: list[DecisionEvent] = []

    def on_tick(self, game, clock) -> None:
        pass

    def on_decision_point(self, game, state, clock) -> None:
        fallback = self.rules.decide(state)  # always run, so its statistics stay current
        ev = DecisionEvent(game.wave + 1, clock.now(), requested=True)
        ans = self.decider.decide(state)
        charge_latency(clock, self.decider, ans.latency_ms)
        ev.arrived_ms, ev.input_tokens = ans.latency_ms, ans.input_tokens
        if ans.ok and ans.decision is not None:
            ev.applied, ev.in_time = ans.decision, True
        else:
            ev.applied, ev.fallback = fallback, True
        game.next_decision = ev.applied
        self.events.append(ev)

    def close(self) -> None:
        if hasattr(self.decider, "close"):
            self.decider.close()
