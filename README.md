# frame-budget

Technical part of a bachelor thesis: can a decision model (Jev, by TypeSafe) make
decisions inside a game's real-time loop, and which architecture makes that
possible within a fixed time budget?

The game is a minimal wave shooter with no graphics and a simulated player. The
decision under study is difficulty: how many enemies the next wave has and how
hard they hit.

- **Start here:** [docs/JEV_GUIDE.md](docs/JEV_GUIDE.md), from API key to first measurement.
- **Each step** has its own branch (`step-0`, `step-1`, ...) and an explanation in `docs/steps/`.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest           # all tests run offline
```

## The steps

| branch | step | main script |
|---|---|---|
| `step-0` | measure Jev's latency in isolation | `scripts/step0_measure_latency.py` |
| `step-1` | fixed-timestep loop, real and simulated clock | `scripts/step1_bare_loop.py` |
| `step-2` | the game and the simulated player | `scripts/step2_fixed_difficulty.py` |
| `step-3` | Hunicke's comfort-zone baseline | `scripts/step3_rules_baseline.py` |
| `step-4` | decider interface, blocking architecture | `scripts/step4_blocking.py` |
| `step-5` | async with rules fallback | `scripts/step5_async.py` |
| `step-6` | latency recording and replay | `scripts/step6_replay.py` |
| `step-7` | cached decisions | `scripts/step7_cache.py` |
| `step-8` | predictive prefetch | `scripts/step8_prefetch.py` |
| `step-9` | experiment runner, consistency run | `scripts/step9_run_experiments.py` |
| `step-10` | analysis and figures | `scripts/step10_analyze.py` |

Each branch builds on the previous one, so `step-10` contains everything.
Results committed so far come from the **simulated** Jev; `docs/JEV_GUIDE.md`
part 7 lists what to run with the real one.
