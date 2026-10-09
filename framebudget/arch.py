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


class AsyncFallback:
    """Step 5: ask in the background, keep the rules in charge until a good answer arrives.

    At a decision point:
      1. The rules decide immediately. That decision is in place right away,
         so the next wave always has a difficulty, whatever the network does.
      2. A request for the same state goes to the channel (non-blocking).
    On every tick, arrived answers are checked:
      - arrived within the deadline (budget_ms after the request) and still
        relevant: it replaces the rules' decision ("in time").
      - arrived after the deadline: discarded, the rules stay ("late").
      - belongs to an older decision point, or the wave already spawned:
        discarded ("stale"). Applying it would mean acting on an old state.
      - failed: discarded, the rules stay.
    """

    name = "async"

    def __init__(self, channel, budget_ms: float):
        self.channel = channel
        self.budget_ms = budget_ms
        self.rules = HunickePolicy()
        self.events: list[DecisionEvent] = []
        self.late = self.stale = self.failed = 0
        self._next_id = 0
        self._latest = -1
        self._by_id: dict[int, DecisionEvent] = {}

    def _request(self, game, state, clock, ev) -> None:
        self._next_id += 1
        self._latest = self._next_id
        self._by_id[self._next_id] = ev
        ev.requested = True
        self.channel.submit(self._next_id, state, clock.now(), tag=("decision", None))

    def on_decision_point(self, game, state, clock) -> None:
        fb = self.rules.decide(state)
        game.next_decision = fb
        ev = DecisionEvent(game.wave + 1, clock.now(), applied=fb, fallback=True)
        self.events.append(ev)
        self._request(game, state, clock, ev)

    def on_tick(self, game, clock) -> None:
        for arr in self.channel.poll(clock.now()):
            self.on_arrival(game, arr)

    def on_arrival(self, game, arr) -> None:
        ev = self._by_id.pop(arr.req_id, None)
        if ev is None:
            return
        ans = arr.answer
        ev.input_tokens += ans.input_tokens
        if not ans.ok or ans.decision is None:
            self.failed += 1
            return
        ev.arrived_ms = arr.elapsed_ms
        if arr.req_id != self._latest or game.wave >= ev.wave:
            self.stale += 1
        elif arr.elapsed_ms <= self.budget_ms:
            game.next_decision = ev.applied = ans.decision
            ev.in_time, ev.fallback = True, False
        else:
            self.late += 1

    def stats(self) -> dict:
        return {"late": self.late, "stale": self.stale, "failed": self.failed}

    def close(self) -> None:
        self.channel.close()
