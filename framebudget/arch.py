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


class CachedAsync(AsyncFallback):
    """Step 7: look the state's signature up first; ask Jev only on a miss.

    Hit:  the cached decision is applied at once. No request, no wait, no cost.
    Miss: exactly like AsyncFallback (rules now, Jev in the background), and when
          Jev's answer arrives, it is stored under the signature, even if it came
          too late to be used this time. The next similar state will hit.

    `cache` is a plain dict, shared across games if you pass the same one in:
    one cache for all players, like a real game server would keep.
    `oracle` (optional answer source) is asked on every hit what it would decide
    for the exact state, to count how often the cached decision differs.
    """

    name = "cache"

    def __init__(self, channel, budget_ms: float, coarse: float = 1.0,
                 cache: dict | None = None, oracle=None):
        super().__init__(channel, budget_ms)
        from .cache import signature

        self.signature = signature
        self.coarse = coarse
        self.cache = {} if cache is None else cache
        self.oracle = oracle
        self.hits = self.misses = self.mismatches = 0

    def on_decision_point(self, game, state, clock) -> None:
        fb = self.rules.decide(state)
        key = self.signature(state, self.coarse)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            d = type(cached)(cached.count, cached.mult, source="cache")
            game.next_decision = d
            self.events.append(DecisionEvent(game.wave + 1, clock.now(), applied=d,
                                             in_time=True, cache_hit=True))
            if self.oracle is not None:
                from .decision import state_to_text

                fresh, _ = self.oracle.answer(state, state_to_text(state))
                self.mismatches += fresh.key() != cached.key()
            return
        self.misses += 1
        game.next_decision = fb
        ev = DecisionEvent(game.wave + 1, clock.now(), applied=fb, fallback=True)
        self.events.append(ev)
        self._next_id += 1
        self._latest = self._next_id
        self._by_id[self._next_id] = ev
        ev.requested = True
        self.channel.submit(self._next_id, state, clock.now(), tag=("decision", key))

    def on_arrival(self, game, arr) -> None:
        ans = arr.answer
        key = arr.tag[1] if arr.tag else None
        if ans.ok and ans.decision is not None and key is not None:
            self.cache.setdefault(key, ans.decision)
        super().on_arrival(game, arr)

    def stats(self) -> dict:
        return {**super().stats(), "hits": self.hits, "misses": self.misses,
                "mismatches": self.mismatches, "cache_size": len(self.cache)}


class PrefetchAsync(CachedAsync):
    """Step 8: guess the next decision point's state when a wave starts, and ask early.

    When a wave spawns we know its size and multiplier and have an estimate of
    the player's kill rate, so we can predict the state at the end of the wave:
    expected damage plus or minus one standard deviation (the same normal model
    the rules use). For each predicted state whose signature is not cached yet,
    a request goes out immediately. Those requests have the whole wave (several
    seconds) to come back, instead of the deadline. When the wave is cleared, the
    real state is looked up in the cache exactly as in Step 7; if the prediction
    landed in the right bucket, it is a hit.

    The cost: requests for predicted states that never happen are wasted.
    """

    name = "prefetch"

    def __init__(self, channel, budget_ms: float, coarse: float = 1.0,
                 cache: dict | None = None, oracle=None, spread=(-1.0, 0.0, 1.0)):
        super().__init__(channel, budget_ms, coarse, cache, oracle)
        self.spread = spread
        self._seen_wave = 0
        self._pending_keys: set = set()
        self._prefetched: set = set()
        self._used: set = set()
        self.prefetch_requests = self.prefetch_tokens = 0

    def on_tick(self, game, clock) -> None:
        if game.phase == "fight" and game.wave != self._seen_wave:
            self._seen_wave = game.wave
            for st in self.predict(game):
                key = self.signature(st, self.coarse)
                if key in self.cache or key in self._pending_keys:
                    continue
                self._pending_keys.add(key)
                self._next_id += 1
                self.prefetch_requests += 1
                self.channel.submit(self._next_id, st, clock.now(), tag=("prefetch", key))
        super().on_tick(game, clock)

    def predict(self, game) -> list:
        """Likely states at the end of the current wave."""
        import statistics

        from .decision import DecisionState
        from .game import MAX_HEALTH, REGEN_PER_WAVE, expected_wave_damage

        rate = self.rules.kill_rate()
        d = game.current
        ratios = self.rules._ratios[-10:]
        bias = statistics.fmean(ratios) if ratios else 1.0
        rel = max(statistics.pstdev(ratios) if len(ratios) >= 3 else 0.0, 0.25)
        mu = expected_wave_damage(d.count, d.mult, rate) * bias
        clear = d.count / rate
        out = []
        for z in self.spread:
            dmg = max(0.0, mu * (1 + z * rel))
            health = min(MAX_HEALTH, max(0.0, game.health - dmg) + REGEN_PER_WAVE)
            out.append(DecisionState(health, MAX_HEALTH, game.wave, d.count, d.mult,
                                     dmg, clear, dmg / clear, rate))
        return out

    def on_decision_point(self, game, state, clock) -> None:
        key = self.signature(state, self.coarse)
        if key in self.cache and key in self._prefetched:
            self._used.add(key)
            n = len(self.events)
            super().on_decision_point(game, state, clock)
            ev = self.events[n]
            ev.applied = type(ev.applied)(ev.applied.count, ev.applied.mult, source="prefetch")
            game.next_decision = ev.applied
            return
        super().on_decision_point(game, state, clock)

    def on_arrival(self, game, arr) -> None:
        kind, key = arr.tag if arr.tag else (None, None)
        if kind == "prefetch":
            self._pending_keys.discard(key)
            self.prefetch_tokens += arr.answer.input_tokens
            if arr.answer.ok and arr.answer.decision is not None:
                self.cache.setdefault(key, arr.answer.decision)
                self._prefetched.add(key)
            return
        super().on_arrival(game, arr)

    def stats(self) -> dict:
        return {**super().stats(), "prefetch_requests": self.prefetch_requests,
                "prefetch_used": len(self._used), "prefetch_tokens": self.prefetch_tokens}
