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
