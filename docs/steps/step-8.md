# Step 8: predictive prefetch

**Question:** can we ask Jev about the next decision point before it happens, so
the answer is waiting when it is needed?

## What was built

| File | What it does |
|---|---|
| `framebudget/arch.py` | Adds `PrefetchAsync` (built on `CachedAsync`). |
| `scripts/step8_prefetch.py` | Prefetch vs cache vs async, every deadline. |

## How it works

When a wave **spawns**, we already know its size and multiplier, and the rules
keep an estimate of the player's kill rate and of how much real waves deviate
from the expected damage (Step 3). From that we predict the state at the
**end** of this wave three times: expected damage, and expected ± one standard
deviation. For each predicted state whose signature is not cached yet, a request
goes out right away. Those requests have the whole wave (3 to 10 seconds) to
come back, not just the deadline.

When the wave is actually cleared, the real state's signature is looked up, as
in Step 7. If one of the predictions fell into the same bucket, it is a hit, and
the decision is applied instantly, even with a 33 ms deadline.

## Results (simulated Jev, your measured latencies, coarseness 1, cache emptied every game)

| deadline | async: Jev in time | prefetch: Jev in time | requests per game: async → prefetch |
|---|---|---|---|
| 33 ms | 0% | 24% | 27 → 73 |
| 250 ms | 14% | 33% | 27 → 72 |
| 350 ms | 79% | 84% | 26 → 66 |
| 500 ms | 93% | 95% | 26 → 64 |
| 750 ms | 100% | 100% | 25 → 63 |

Prefetch is the only architecture that gets Jev decisions in at a 33 ms
deadline, but it pays for that with about 2.7 times the requests, and only about
1 in 12 prefetched predictions is actually used (`prefetch_used`). The prediction
misses mostly because the kill rate of the next wave is noisy. Things to try if
you keep this step: a coarser signature (c = 2), or more predicted states.

This is the riskiest part, as your plan says. It works and is tested, so it can
stay in the comparison, but nothing later depends on it.

## Run it

```bash
python -m scripts.step8_prefetch
python -m scripts.step8_prefetch --coarse 2
```
