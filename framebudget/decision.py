"""What the decider sees (DecisionState) and what it returns (Decision).

Everything that makes a difficulty decision, the hand-written rules as well as
Jev, works on these two types. Keeping them small and explicit is what lets us
swap deciders without touching the game.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

# The decision space. Both the rule-based policy and Jev pick from these lists,
# so their decisions are directly comparable.
ENEMY_COUNTS = (3, 5, 8, 12)
DAMAGE_MULTS = (0.75, 1.0, 1.25, 1.5)


@dataclass(frozen=True)
class Decision:
    """Difficulty of the next wave."""

    count: int  # how many enemies the next wave contains
    mult: float  # damage multiplier applied to every enemy of that wave
    source: str = "rules"  # who made it: "rules", "jev", "cache", "prefetch", ...

    def key(self) -> tuple[int, float]:
        return (self.count, self.mult)


@dataclass(frozen=True)
class DecisionState:
    """A snapshot of the game, taken at a decision point (a wave was cleared)."""

    health: float
    max_health: float
    wave: int  # number of the wave that was just cleared
    last_count: int  # enemies in that wave
    last_mult: float  # its damage multiplier
    last_wave_damage: float  # damage the player took during that wave
    last_clear_time: float  # seconds it took the player to clear it
    dps_recent: float  # damage taken per second over the last 10 s
    kill_rate: float  # player kills per second over the last 10 s

    def as_dict(self) -> dict:
        return asdict(self)


def state_to_text(s: DecisionState) -> str:
    """The `state` string we send to Jev.

    Numbers are rounded so that the text is stable: two runs with the same seed
    produce byte-identical texts, which Step 6 (replay) relies on.
    """
    return (
        f"Action game, difficulty tuning. Player health: {s.health:.0f} of {s.max_health:.0f}. "
        f"Wave {s.wave} was just cleared. It had {s.last_count} enemies with damage "
        f"multiplier {s.last_mult:g}. The player took {s.last_wave_damage:.0f} damage in it "
        f"and needed {s.last_clear_time:.1f} s to clear it. Over the last 10 s the player "
        f"took {s.dps_recent:.1f} damage per second and killed {s.kill_rate:.2f} enemies per second."
    )
