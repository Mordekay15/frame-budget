"""Latency models: "how long does Jev take to answer?"

`LognormalLatency` is a synthetic stand-in, used when no measurements exist.
Network latencies are skewed to the right (most requests are fast, a few are
very slow), and a lognormal distribution has exactly that shape. Its defaults
are fitted to the Step 0 measurement (12 Oct 2026, warm): median 310 ms, and
sigma 0.3 reproduces the measured p95 (506 ms) and p99 (617 ms).
"""

from __future__ import annotations

import math
import random


class LognormalLatency:
    def __init__(self, median_ms: float = 310.0, sigma: float = 0.30, seed: int = 0):
        self.mu = math.log(median_ms)
        self.sigma = sigma
        self.rng = random.Random(seed)

    def sample_ms(self) -> float:
        return self.rng.lognormvariate(self.mu, self.sigma)


class EmpiricalLatency:
    """Draws latencies at random from real measurements (e.g. the Step 0 CSV).

    Resampling measured values keeps the true shape of the distribution,
    including its slow tail, without assuming any formula.
    """

    def __init__(self, csv_path: str, condition: str = "warm", seed: int = 0):
        import csv

        with open(csv_path, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("condition", condition) == condition]
        # A failed request is treated as never arriving.
        self.values = [float(r["latency_ms"]) if r.get("ok", "1") == "1" else math.inf for r in rows]
        if not self.values:
            raise ValueError(f"no '{condition}' rows in {csv_path}")
        self.rng = random.Random(seed)

    def sample_ms(self) -> float:
        return self.rng.choice(self.values)

    @classmethod
    def from_values(cls, values: list[float], seed: int = 0) -> "EmpiricalLatency":
        m = cls.__new__(cls)
        m.values, m.rng = values, random.Random(seed)
        return m


MEASURED_CSV = "results/step0/jev_latency.csv"


def resolve(spec: str) -> str:
    """'measured' means the Step 0 CSV if it exists, otherwise the synthetic model."""
    if spec == "measured":
        from pathlib import Path

        return MEASURED_CSV if Path(MEASURED_CSV).exists() else "synthetic"
    return spec


def latency_model(spec: str, seed: int = 0):
    """'measured', 'synthetic' or a path to a CSV with a latency_ms column."""
    spec = resolve(spec)
    if spec == "synthetic":
        return LognormalLatency(seed=seed)
    return EmpiricalLatency(spec, seed=seed)
