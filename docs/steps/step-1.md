# Step 1: the bare loop

**Question:** how precisely can a plain Python loop keep a 33 ms rhythm when it
does no work at all? This is the baseline: every overrun in later steps is
measured against it.

## What was built

| File | What it does |
|---|---|
| `framebudget/clock.py` | `RealClock` (the machine's monotonic clock, real sleeping) and `SimClock` (virtual time). |
| `framebudget/loop.py` | `run_loop`: the fixed-timestep loop, and `tick_summary`: the numbers that describe a run. |
| `scripts/step1_bare_loop.py` | 10 000 empty ticks on the real clock, CSV + summary + two plots. |

## How it works, and why

- **Absolute schedule.** Tick *i* is due at `start + i * 33 ms`. A naive loop does
  `sleep(33 ms)` after each tick, and since every sleep wakes up a little late
  the errors add up: after 10 000 ticks the loop is seconds behind. Aiming each
  tick at its own fixed target means an error in one tick is corrected by the next.
- **Sleep, then spin.** `time.sleep` is only accurate to around a millisecond (on
  some Windows setups, much worse). The clock sleeps until 2 ms before the target
  and then checks the time in a tight loop for the rest. That costs a little CPU
  and gives microsecond precision.
- **What is recorded per tick.** *Period*: time since the previous tick started
  (should be 33 ms). *Lateness*: actual start minus scheduled start (drift).
  *Work*: how long the tick itself took (0 here; Jev calls later).
- **Fixed timestep.** The game always advances by exactly 33 ms of game time per
  tick, no matter how long the tick really took. So the game's behaviour does not
  depend on how fast the computer is; only the timing log does.
- **Two clocks.** `SimClock` runs the same loop with virtual time and no sleeping.
  It is used from Step 2 on to run games thousands of times faster than real time,
  and with exactly repeatable results.

## Run it

```bash
python -m scripts.step1_bare_loop          # ~5.5 minutes
```

The committed `results/step1/` comes from the cloud machine this was developed
on; run it again on your laptop for the number you report, since the thesis
should state the machine the experiments ran on.

## Done when

10 000 ticks ran, `final_drift_ms` is bounded (it does not grow with the number of
ticks), and `tick_hist.png` shows a narrow peak at 33 ms.
