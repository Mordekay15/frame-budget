# Step 9: metrics collection and the experiment runner

**Question:** all architectures, all deadlines, all skills, many repetitions: one dataset.

## What was built

| File | What it does |
|---|---|
| `framebudget/experiment.py` | `Setup` (where answers and latencies come from) and `cells` (the experiment design). |
| `framebudget/replay.py` | Adds `LiveAnswers`, the live Jev as an answer source, for recording a sweep. |
| `scripts/step9_run_experiments.py` | The sweep → `results/step9/dataset.csv` + `meta.json`. |
| `scripts/step9_consistency.py` | The consistency run → `results/step9/consistency.csv`. |

## The design

| factor | levels |
|---|---|
| architecture | rules, blocking, async, cache, prefetch |
| deadline | 33, 100, 250, 500 ms (async, cache, prefetch only; rules and blocking have none) |
| bot skill | weak, medium, strong |
| repetitions | 30 games per cell (`--reps`) |

That is 3·30 (rules) + 3·30 (blocking) + 3·4·3·30 = **1 260 games**, about 15 seconds offline.

**Common random numbers.** A game's randomness *and its latency sequence*
depend only on (skill, seed), not on the architecture. So "async vs prefetch at
seed 7" is the same player facing the same network, and the differences come
from the architectures. This makes the comparison much sharper for the same
number of games, and it is a standard technique worth naming in the methodology chapter.

**Independent games.** The cache starts empty in every game, so games are
independent repetitions and ordinary confidence intervals are valid. (Step 7's
shared cache answered a different question: how a server-wide cache behaves.)

## One row per game (`dataset.csv`)

| column | meaning |
|---|---|
| `arch`, `budget_ms`, `skill`, `seed` | the cell |
| `deadline_met` | **metric 1**: share of decisions made by the model (or cache) within the deadline |
| `fallback_rate` | **metric 2**: share of decisions where the rules stood in |
| `tokens_total`, `cost_per_hour_usd`, `requests_per_hour` | **metric 4**: cost, including prefetch requests |
| `died`, `waves_cleared`, `bored`, `in_band`, `danger` | how the game felt |
| `tick_p99_ms`, `tick_max_ms`, `overruns` | the loop's timing |
| `late`, `stale`, `failed`, `hits`, `misses`, `prefetch_*` | architecture counters |

**Metric 3, consistency**, is a separate run because it needs identical input:
12 probe states, each asked 30 times. It is measured at two levels:
the model's raw answers, and what each architecture would actually *apply*. An
architecture can be less consistent than its model. Async with a 250 ms deadline
mixes Jev's answers with the rules' whenever latency crosses the deadline, so
the same state gets different decisions depending on network luck. In the
simulated run it is the least consistent configuration of all (`consistency.md`).

## Running it with the real Jev

See `docs/JEV_GUIDE.md`, part 7. In short: one **record** run asks the live Jev
for every decision of the sweep and stores the answers. One **replay** run then
produces the final, reproducible dataset from the stored answers and your
measured latencies.

```bash
python -m scripts.step9_run_experiments                       # offline
python -m scripts.step9_consistency
```
