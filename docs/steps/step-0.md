# Step 0: measure the model in isolation

**Question:** how long does Jev take to answer a request that looks like the real one?
Every later choice (which deadlines to test, whether a 33 ms deadline makes any
sense) depends on this distribution.

## What was built

| File | What it does |
|---|---|
| `framebudget/decision.py` | `DecisionState` (what a decider sees) and `Decision` (what it returns). `state_to_text` turns a state into the text we send to Jev. |
| `framebudget/jev.py` | The Jev client. One HTTPS connection kept open between requests, a timer around each request, answers parsed into a `Decision`. Standard library only. |
| `framebudget/fakejev.py`, `framebudget/latency.py` | An offline stand-in for Jev with lognormal latency (median 220 ms), so everything runs without a key. |
| `scripts/jev_hello.py` | One request, prints the full answer. Start here. |
| `scripts/step0_measure_latency.py` | The measurement run: warm, cold and same-state conditions. |
| `scripts/step0_analyze.py` | Percentiles, share under each deadline, cost per hour, consistency, plots. |

## How it works, and why

- **Timing.** `time.perf_counter()` is read right before the request is sent and
  right after the full answer is read. It is a monotonic clock with sub-microsecond
  resolution, unlike `time.time()`, which can jump when the system clock is adjusted.
- **Warm vs cold.** Opening an HTTPS connection costs a TCP handshake plus a TLS
  handshake: several network round trips. A game opens one connection and keeps
  it, so `warm` is the realistic number. `cold` shows the price of the first
  request, or of a connection that dropped.
- **Random states.** Every warm/cold request has a different state, so that no
  cache on the provider side makes the numbers look better than they are.
- **Same state.** 30 identical requests tell us whether Jev is deterministic.
  That is the consistency metric, measured early.
- **Failures are data.** A timeout or error is written as a row with `ok=0`. For
  the "share under X ms" columns it counts as a miss, because in the game a
  failed request is exactly as useless as a late one.
- **Percentiles.** The median says what is typical; p95 and p99 say how bad the
  slow tail is. In a real-time system the tail matters more than the average:
  at one decision every 5 s, a 1-in-100 event happens about every 8 minutes.

## Run it

See `docs/JEV_GUIDE.md`, parts 4 to 6. Offline dry run without a key:

```bash
python -m scripts.step0_measure_latency --fake --out results/step0/fake/jev_latency.csv
python -m scripts.step0_analyze results/step0/fake/jev_latency.csv
```

## Done when

`results/step0/jev_latency.csv` holds a real run, `summary.md` and the two plots
are committed, and we have picked the deadlines. The working assumption until
then (from the published p50 of about 220 ms) is to test 33, 100, 250 and 500 ms.
