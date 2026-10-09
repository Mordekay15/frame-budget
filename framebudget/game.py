"""The game: a player with health, waves of enemies, and a simulated player (bot).

Rules of one wave:
  - The wave spawns `count` enemies, each dealing `BASE_DPS * mult` damage per
    second to the player while it is alive.
  - The bot kills enemies one at a time. Time to the next kill is random
    (exponential) with mean 1 / kill_rate, so a bot with kill rate 2 kills two
    enemies per second on average, but with realistic streaks and droughts.
  - When the last enemy dies the wave is cleared: the player regains
    REGEN_PER_WAVE health, the game takes a snapshot (a decision point), and
    after a pause of WAVE_GAP_S seconds the next wave spawns, using whatever
    decision is current at that moment.

Why does damage grow with count squared? While the bot works through n enemies,
n are alive, then n-1, ..., then 1, so the total damage of a wave is about
BASE_DPS * mult * n(n+1)/2 / kill_rate. Doubling the wave size roughly
quadruples its damage. That makes `count` the strong lever and `mult` the fine one.

The game only advances in fixed steps of dt (game time). It knows nothing
about wall-clock time, threads or Jev; that is the job of the architectures.
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

from .decision import Decision, DecisionState

MAX_HEALTH = 100.0
BASE_DPS = 2.0  # damage per second of one enemy at mult 1.0
REGEN_PER_WAVE = 15.0
WAVE_GAP_S = 1.0
WAVES = 30
STATS_WINDOW_S = 10.0

# Skill = average kills per second. Calibrated (scripts/step2_fixed_difficulty.py)
# so that at the default difficulty the weak bot dies, the medium bot is under
# pressure and the strong bot is never in danger.
SKILLS = {"weak": 1.2, "medium": 2.0, "strong": 3.5}
DEFAULT_DECISION = Decision(5, 1.0, source="default")


@dataclass
class Bot:
    skill: float  # mean kills per second
    wobble: float = 0.15  # per-wave variation of skill (log-normal sigma): good and bad waves

    def wave_rate(self, rng: random.Random) -> float:
        return self.skill * rng.lognormvariate(0.0, self.wobble)


@dataclass
class WaveRecord:
    wave: int
    count: int
    mult: float
    source: str
    damage: float
    clear_time: float
    health_after: float


@dataclass
class Game:
    bot: Bot
    rng: random.Random
    dt: float
    waves_total: int = WAVES
    health: float = MAX_HEALTH
    t: float = 0.0
    wave: int = 0  # number of the current (or last) wave
    enemies: int = 0
    current: Decision = DEFAULT_DECISION  # decision of the wave being fought
    next_decision: Decision = DEFAULT_DECISION  # used when the next wave spawns
    phase: str = "gap"  # "fight" or "gap"
    gap_left: float = WAVE_GAP_S
    over: bool = False
    died: bool = False
    waves_log: list[WaveRecord] = field(default_factory=list)
    health_trace: list[float] = field(default_factory=list)  # health fraction per tick

    def __post_init__(self):
        self._rate = self.bot.skill
        self._next_kill = 0.0
        self._wave_start = 0.0
        self._wave_damage = 0.0
        self._recent_damage: deque[tuple[float, float]] = deque()  # (time, damage)
        self._recent_kills: deque[float] = deque()

    # --- one tick -------------------------------------------------------
    def step(self) -> DecisionState | None:
        """Advance the game by dt. Returns a snapshot when a wave was just cleared."""
        if self.over:
            return None
        self.t += self.dt
        snapshot = None
        if self.phase == "gap":
            self.gap_left -= self.dt
            if self.gap_left <= 1e-9:
                self._spawn()
        else:
            dmg = self.enemies * BASE_DPS * self.current.mult * self.dt
            self.health -= dmg
            self._wave_damage += dmg
            self._recent_damage.append((self.t, dmg))
            # Kills that happen within this tick.
            self._next_kill -= self.dt
            while self._next_kill <= 0 and self.enemies > 0:
                self.enemies -= 1
                self._recent_kills.append(self.t)
                self._next_kill += self.rng.expovariate(self._rate)
            if self.health <= 0:
                self.health = 0.0
                self.over = self.died = True
            elif self.enemies == 0:
                snapshot = self._clear()
        self._trim()
        self.health_trace.append(self.health / MAX_HEALTH)
        return snapshot

    def _spawn(self) -> None:
        self.wave += 1
        self.current = self.next_decision
        self.enemies = self.current.count
        self.phase = "fight"
        self._rate = self.bot.wave_rate(self.rng)
        self._next_kill = self.rng.expovariate(self._rate)
        self._wave_start = self.t
        self._wave_damage = 0.0

    def _clear(self) -> DecisionState | None:
        self.health = min(MAX_HEALTH, self.health + REGEN_PER_WAVE)
        self.waves_log.append(WaveRecord(
            self.wave, self.current.count, self.current.mult, self.current.source,
            self._wave_damage, self.t - self._wave_start, self.health,
        ))
        if self.wave >= self.waves_total:
            self.over = True
            return None
        self.phase, self.gap_left = "gap", WAVE_GAP_S
        return self.snapshot()

    def _trim(self) -> None:
        cutoff = self.t - STATS_WINDOW_S
        while self._recent_damage and self._recent_damage[0][0] < cutoff:
            self._recent_damage.popleft()
        while self._recent_kills and self._recent_kills[0] < cutoff:
            self._recent_kills.popleft()

    # --- what deciders see ---------------------------------------------
    def snapshot(self) -> DecisionState:
        window = min(STATS_WINDOW_S, max(self.t, self.dt))
        last = self.waves_log[-1] if self.waves_log else None
        return DecisionState(
            health=self.health,
            max_health=MAX_HEALTH,
            wave=self.wave,
            last_count=last.count if last else 0,
            last_mult=last.mult if last else 1.0,
            last_wave_damage=last.damage if last else 0.0,
            last_clear_time=last.clear_time if last else 0.0,
            dps_recent=sum(d for _, d in self._recent_damage) / window,
            kill_rate=len(self._recent_kills) / window,
        )

    def wave_damages(self) -> list[float]:
        return [w.damage for w in self.waves_log]


def experience_metrics(health_trace: list[float]) -> dict:
    """How the game felt, as numbers.

    bored:   share of time with health at or above 90%: nothing threatens the player.
    danger:  share of time at or below 20%: one bad moment from death.
    in_band: the rest, the "challenged but OK" zone we want the player to stay in.
    """
    n = max(1, len(health_trace))
    bored = sum(h >= 0.9 for h in health_trace) / n
    danger = sum(h <= 0.2 for h in health_trace) / n
    return {
        "bored": bored,
        "danger": danger,
        "in_band": 1.0 - bored - danger,
        "mean_health": sum(health_trace) / n,
        "min_health": min(health_trace) if health_trace else 1.0,
    }


def expected_wave_damage(count: int, mult: float, kill_rate: float) -> float:
    """Mean damage of a wave (see module docstring): BASE_DPS * mult * n(n+1)/2 / rate."""
    return BASE_DPS * mult * count * (count + 1) / 2 / max(kill_rate, 1e-6)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
