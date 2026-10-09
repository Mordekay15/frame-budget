# Step 5: asynchronous with fallback

**Question:** can the game use Jev without ever waiting for it?

## What was built

| File | What it does |
|---|---|
| `framebudget/channel.py` | How requests travel without blocking: `SimChannel` (virtual time) and `ThreadChannel` (real worker threads). |
| `framebudget/arch.py` | Adds `AsyncFallback`. |
| `scripts/step5_async.py` | All budgets × skills, on the simulated or the real clock, with the simulated or the live Jev. |

## How it works

At a decision point (a wave was just cleared):

1. **The rules decide at once**, and their decision is put in place. From this
   moment the next wave has a difficulty, whatever happens on the network.
2. **A request goes out in the background** with the same state. The tick returns immediately.

On every tick the loop asks the channel "did anything arrive?" (`poll`, which
never waits). An answer is then one of:

| case | what happens | counter |
|---|---|---|
| arrived within the deadline | replaces the rules' decision | `deadline_met` |
| arrived after the deadline | discarded, rules stay | `late` |
| belongs to an older decision point, or the wave already started | discarded: it was computed for a state that no longer exists | `stale` |
| request failed | discarded, rules stay | `failed` |

### The concurrency part, on the real clock

`ThreadChannel` keeps a small pool of worker threads. `submit()` hands the
request to the pool and returns; a worker sends the HTTP request, waits for the
answer, stamps the arrival time and puts it on a `queue.Queue`. The loop drains
that queue with `get_nowait()`, which never blocks. Two details:

- **One connection per worker.** Python's `http.client` connection is not safe
  to share between threads, so each worker creates its own Jev client on first use (`threading.local`).
- **Python's GIL.** Only one thread runs Python code at a time, but a thread that
  waits for the network releases it. So the loop keeps ticking while workers wait;
  that is exactly the case where threads work well in Python.

### Why the deadline is not the 33 ms tick

The tick budget (33 ms) is never touched: no tick waits for anything. The
*deadline* is how long the game is willing to let the rules' decision stand
before Jev's answer is no longer accepted. In this game the next wave spawns
1 s after the decision point, so any deadline up to 1 s is possible; we test 33,
100, 250 and 500 ms, from "Jev must answer within one tick" to "Jev may take half a second".

## Results (simulated, synthetic latency; `results/step5/summary.md`)

| deadline | Jev answer used | rules fallback | longest tick |
|---|---|---|---|
| 33 ms | 0% | 100% | 33 ms |
| 100 ms | 1% | 99% | 33 ms |
| 250 ms | 66% | 34% | 33 ms |
| 500 ms | 99.5% | 0.5% | 33 ms |

The tick is back inside budget, and the share of Jev decisions simply follows
the latency distribution: it is the Step 0 "share under X ms" number. That is
the key observation for the thesis: **with async, the deadline decides how much
of the game Jev controls, and below the median latency, Jev controls almost nothing.**
Steps 7 and 8 try to change that.

`results/step5/real_clock/` is the same experiment for one game per skill on the
real clock with real threads (deadline 250 ms). It shows the same split (69% Jev,
31% rules). The 99th-percentile tick is 33.4 ms and no tick's own work ever
exceeded the budget; the single longest tick (69 ms) is operating-system
scheduling jitter on the shared cloud machine, the same kind Step 1 measures.

## Run it

```bash
python -m scripts.step5_async
python -m scripts.step5_async --latency results/step0/jev_latency.csv
python -m scripts.step5_async --live --budgets 250 --games 1    # real Jev, ~5 minutes
```
