"""Latency models: "how long does Jev take to answer?"

`LognormalLatency` is a synthetic stand-in, used until real measurements exist.
Network latencies are skewed to the right (most requests are fast, a few are
very slow), and a lognormal distribution has exactly that shape. Its default
median of 220 ms is OpenRouter's published p50 for Jev; sigma 0.35 gives a p99
of roughly 500 ms, matching TypeSafe's "70 to 500 ms" claim.
"""

from __future__ import annotations

import math
import random


class LognormalLatency:
    def __init__(self, median_ms: float = 220.0, sigma: float = 0.35, seed: int = 0):
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


def latency_model(spec: str, seed: int = 0):
    """'synthetic' or a path to a CSV with a latency_ms column."""
    if spec == "synthetic":
        return LognormalLatency(seed=seed)
    return EmpiricalLatency(spec, seed=seed)
