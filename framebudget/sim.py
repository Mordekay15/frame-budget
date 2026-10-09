"""Running one game (an episode) with some architecture in charge of difficulty.

An architecture is any object with two methods:

    on_decision_point(game, state, clock)  called when a wave was just cleared
    on_tick(game, clock)                   called at the start of every tick

It changes difficulty by setting `game.next_decision`. The game spawns the next
wave WAVE_GAP_S seconds after the decision point, with whatever is in
`next_decision` at that moment.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .clock import SimClock
from .decision import Decision
from .game import SKILLS, Bot, Game, experience_metrics
from .loop import TICK_S, run_loop, tick_summary


@dataclass
class DecisionEvent:
    """One decision point and what came of it. Filled in by the architectures."""

    wave: int  # the wave this decision is for
    requested_at: float  # game-loop time of the decision point (s)
    applied: Decision | None = None
    requested: bool = False  # was a request sent to the model?
    arrived_ms: float | None = None  # model latency, if an answer came back at all
    in_time: bool = False  # did it arrive within the deadline?
    fallback: bool = False  # did the rules decide because the model was late/absent?
    cache_hit: bool = False
    input_tokens: int = 0


class FixedDifficulty:
    """Step 2: no adjustment at all, every wave has the same difficulty."""

    name = "fixed"

    def __init__(self, decision: Decision):
        self.decision = decision
        self.events: list[DecisionEvent] = []

    def on_tick(self, game: Game, clock) -> None:
        pass

    def on_decision_point(self, game: Game, state, clock) -> None:
        game.next_decision = self.decision
        self.events.append(DecisionEvent(game.wave + 1, clock.now(), applied=self.decision))


@dataclass
class EpisodeResult:
    arch: str
    skill: str
    seed: int
    died: bool
    waves_cleared: int
    duration_s: float
    experience: dict
    ticks: dict
    events: list[DecisionEvent] = field(default_factory=list)
    waves: list = field(default_factory=list)

    def row(self) -> dict:
        """A flat dict, one row of the experiment dataset."""
        ev = [e for e in self.events if e.wave > 1]
        req = [e for e in ev if e.requested]
        n = max(1, len(ev))
        return {
            "arch": self.arch, "skill": self.skill, "seed": self.seed,
            "died": int(self.died), "waves_cleared": self.waves_cleared,
            "duration_s": round(self.duration_s, 3),
            **{k: round(v, 5) for k, v in self.experience.items()},
            "decisions": len(ev),
            "requests": len(req),
            "deadline_met": sum(e.in_time for e in ev) / n,
            "fallback_rate": sum(e.fallback for e in ev) / n,
            "cache_hit_rate": sum(e.cache_hit for e in ev) / n,
            "input_tokens": sum(e.input_tokens for e in self.events),
            "tick_p99_ms": round(self.ticks["period_p99_ms"], 4),
            "tick_max_ms": round(self.ticks["period_max_ms"], 4),
            "overruns": self.ticks["overruns"],
        }


def run_episode(arch, skill: str = "medium", seed: int = 0, clock=None,
                waves: int | None = None, max_ticks: int = 200_000) -> EpisodeResult:
    """Play one game to the end (death or last wave) and collect everything."""
    clock = clock or SimClock()
    rng = random.Random(seed)
    game = Game(Bot(SKILLS[skill]), rng, TICK_S)
    if waves:
        game.waves_total = waves
    game.next_decision = getattr(arch, "first_decision", game.next_decision)

    def tick(i: int) -> bool:
        arch.on_tick(game, clock)
        snap = game.step()
        if snap is not None:
            arch.on_decision_point(game, snap, clock)
        return game.over

    records = run_loop(tick, clock, n_ticks=max_ticks)
    if hasattr(arch, "close"):
        arch.close()
    return EpisodeResult(
        arch=getattr(arch, "name", type(arch).__name__),
        skill=skill, seed=seed, died=game.died,
        waves_cleared=len(game.waves_log), duration_s=game.t,
        experience=experience_metrics(game.health_trace),
        ticks=tick_summary(records), events=list(getattr(arch, "events", [])),
        waves=game.waves_log,
    )
