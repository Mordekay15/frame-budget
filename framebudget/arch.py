"""Architectures: who decides the next wave's difficulty, and when.

Step 3 adds the rule-based baseline. Later steps add the Jev architectures.
"""

from __future__ import annotations

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
