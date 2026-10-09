"""Step 9: building the architectures for one experiment cell, the same way every time.

One *cell* is (architecture, deadline, skill, seed). Everything random in a cell
is derived from those values, so a cell always produces the same row.

Common random numbers: for a given (skill, seed), every architecture sees the
same game randomness AND the same sequence of latencies. Differences between
architectures are then caused by the architectures, not by luck, which makes
comparisons much sharper with the same number of games.
"""

from __future__ import annotations

import zlib

from .arch import AsyncFallback, Blocking, CachedAsync, PrefetchAsync, RulesOnly
from .channel import SimChannel
from .deciders import FakeAnswers, SimulatedJev
from .latency import EmpiricalLatency, LognormalLatency

ARCHS = ("rules", "blocking", "async", "cache", "prefetch")
NO_BUDGET = ("rules", "blocking")  # these never use a deadline


def cell_seed(*parts) -> int:
    return zlib.crc32(repr(parts).encode())


class Setup:
    """Where answers and latencies come from, for every cell of a sweep.

    answers: "fake"             the offline FakeAnswers
             an answer source   e.g. StoreAnswers (replay) or StoreAnswers + LiveAnswers (record)
    latency: "synthetic"        lognormal, median 220 ms
             path to a CSV      measured latencies (Step 0 file or a Step 6 recording)
    """

    def __init__(self, answers="fake", latency: str = "synthetic", coarse: float = 1.0):
        self.answers = answers
        self.latency = latency
        self.coarse = coarse
        self._csv_values = None

    def latency_model(self, skill: str, seed: int):
        s = cell_seed("latency", skill, seed)
        if self.latency == "synthetic":
            return LognormalLatency(seed=s)
        if self._csv_values is None:
            self._csv_values = EmpiricalLatency(self.latency).values
        return EmpiricalLatency.from_values(self._csv_values, s)

    def answer_source(self, skill: str, seed: int):
        if self.answers == "fake":
            return FakeAnswers(seed=cell_seed("answers", skill, seed))
        return self.answers

    def arch(self, name: str, budget_ms: float | None, skill: str, seed: int):
        if name == "rules":
            return RulesOnly()
        jev = SimulatedJev(self.answer_source(skill, seed), self.latency_model(skill, seed))
        if name == "blocking":
            return Blocking(jev)
        ch = SimChannel(jev)
        if name == "async":
            return AsyncFallback(ch, budget_ms)
        if name == "cache":
            return CachedAsync(ch, budget_ms, coarse=self.coarse)
        if name == "prefetch":
            return PrefetchAsync(ch, budget_ms, coarse=self.coarse)
        raise ValueError(name)


def cells(archs, budgets, skills, reps):
    for name in archs:
        for budget in ([None] if name in NO_BUDGET else budgets):
            for skill in skills:
                for seed in range(reps):
                    yield name, budget, skill, seed
