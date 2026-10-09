# Step 4: the decider interface and the blocking architecture

**Question:** what happens if the game simply waits for Jev? This is the naive
design, built on purpose to measure how bad it is.

## What was built

| File | What it does |
|---|---|
| `framebudget/deciders.py` | The interface `decide(state) -> Answer` and its implementations: `RuleDecider`, `LiveJevDecider` (the real Jev), `SimulatedJev` (fake answers + a latency model), `FakeAnswers`. |
| `framebudget/latency.py` | Adds `EmpiricalLatency`: draws latencies from your Step 0 CSV. |
| `framebudget/arch.py` | Adds `Blocking`. |
| `scripts/step4_blocking.py` | Blocking vs rules, tick statistics, timeline plot. |

## Two ideas worth understanding

**1. Separate *what* is decided from *how* it is called.** A *decider* answers one
question: given this state, what is the decision? An *architecture* decides
when to ask, how long to wait and what to do meanwhile. Because the two are
separate, the same Jev can sit behind the blocking, async, cache and prefetch
architectures, and the comparison between architectures is fair.

An `Answer` carries the decision *and its cost*: latency and tokens. `ok=False`
means no usable decision, and then every architecture falls back to the rules.

**2. A simulated Jev = answers + latency.** `SimulatedJev` gets its decisions from
`FakeAnswers` (a heuristic aiming for about 60% health, with some noise) and its
timing from a latency model: the synthetic lognormal from Step 0, or your
measured CSV. On the simulated clock, a "blocking call" simply moves virtual time
forward by the latency, so the effect on the loop is the same as for real, but a
whole experiment takes seconds.

## What blocking does to the loop

The tick that reaches a decision point lasts as long as the request: about
200 ms instead of 33 ms. The loop is then behind schedule, so the next few ticks
run immediately, one after the other, to catch up (the zero-length ticks right
after each spike in `tick_timeline.png`). In a real game those catch-up ticks are
visible as a freeze followed by a jump.

## Results (simulated, synthetic latency; `results/step4/summary.md`)

- **Every** decision point overruns the 33 ms budget.
- Blowout factor (longest tick / 33 ms): **12x** on average per game, **23x** in the worst game.

Rerun with your measured latencies (`--latency results/step0/jev_latency.csv`) and
once with `--live` to get the real number for the results chapter.

## Run it

```bash
python -m scripts.step4_blocking
python -m scripts.step4_blocking --latency results/step0/jev_latency.csv
python -m scripts.step4_blocking --live      # needs your key, ~5 minutes
```
