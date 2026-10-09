# Step 7: cached decisions

**Question:** if similar states deserve similar decisions, can we reuse earlier
answers and skip the wait entirely? And how similar is "similar"?

## What was built

| File | What it does |
|---|---|
| `framebudget/cache.py` | `signature(state, c)`: the coarse key of a state. |
| `framebudget/arch.py` | Adds `CachedAsync` (built on `AsyncFallback`). |
| `scripts/step7_cache.py` | Hit rate, mismatch and decisions-in-time against coarseness. |

## How it works

The signature keeps four things, each rounded into buckets whose size grows
with the coarseness `c`:

| part | bucket size |
|---|---|
| health | 10·c (c = 1: "rounded to tens") |
| size of the wave just cleared | exact |
| damage trend: damage of the last wave minus regeneration | 10·c |
| kill rate in the last wave | 0.5·c kills/s |

At a decision point, the signature is looked up:

- **hit:** the stored decision is applied at once. No request, no wait, no tokens.
- **miss:** exactly Step 5 (rules now, Jev in the background). When Jev's answer
  arrives it is stored under that signature, **even if it is too late** to be
  used this time. A late answer is useless for its own decision point, but it is
  still a valid answer for the next similar state.

## The real result: the trade-off curve

`scripts/step7_cache.py` runs 30 games per skill for each `c` in 0.25 … 8, with
one cache shared by all games (like a cache on a game server) and a 250 ms deadline.
For each hit it also checks what a noise-free decider would have chosen for the
*exact* state. **Mismatch** is the share of hits where that differs: how much
information the buckets threw away.

| c | hit rate | mismatch | in time (Jev or cache) | requests per game |
|---|---|---|---|---|
| 0.25 | 11% | 15% | 70% | 23 |
| 0.5 | 43% | 25% | 81% | 15 |
| 1 | 75% | 42% | 92% | 6 |
| 2 | 90% | 56% | 97% | 2.4 |
| 4 | 96% | 68% | 99% | 1.0 |
| 8 | 98% | 75% | 99.5% | 0.4 |

(simulated Jev and synthetic latency, `results/step7/summary.md`)

Hit rate and mismatch rise together: that is the "too coarse / too fine" problem
from your plan, now as a curve (`hit_rate_vs_coarseness.png`). The knee is around
c = 0.5 to 1. Rerun it with the real Jev's answers (Step 9) before drawing conclusions,
because the mismatch depends on how sensitive the decider is to small changes in state.

## Run it

```bash
python -m scripts.step7_cache
```
