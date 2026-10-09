# Step 6: latency recording and replay

**Question:** how can an experiment that talks to a network service be repeated exactly?

## What was built

| File | What it does |
|---|---|
| `framebudget/replay.py` | `RecordingDecider` (records live answers and latencies), `RecordedLatency` (plays latencies back in order), `AnswerStore` and `StoreAnswers` (state text → Jev's answer). |
| `scripts/step6_replay.py` | Records a run with the live Jev, or replays one twice and checks that everything is identical. |

## What varies between two runs, and how each is pinned down

| source of variation | pinned down by |
|---|---|
| the bot's randomness | the seed (since Step 2) |
| thread timing, computer speed | the simulated clock (since Step 1) |
| network latency | `latencies.csv`: replayed in recorded order |
| Jev's answer (if it varies at all) | `answers.json`: the recorded answer for each state text |

The state text is built from rounded numbers (`state_to_text`), and the game is
seeded, so the same game produces exactly the same texts. That is why a recorded
answer can be found again.

**Recording** runs the experiment on the simulated clock while asking the live
Jev. Each answer is used immediately, and its *real* latency is charged as virtual
time. So the recording run is a normal experiment, just with real network
timings. **Replaying** uses the stored answers and latencies instead. It
reproduces the recorded run exactly, without a key or network, as often as you like.

## Results

With the synthetic demo recording (`results/step6/summary_synthetic-demo.md`):
replay 1, replay 2 and the recorded run have the same SHA-256 digest. The test
`tests/test_step6.py` checks the same thing on every run of the test suite.

## Limits worth a sentence in the thesis

- If the same state text occurs twice during recording and Jev answered
  differently, the store keeps the last answer, and a replay can differ from
  the *recorded* run (never from another replay).
- A failed request is replayed as a timeout (10 s). The decision is the same
  (rules fallback), but when the failure is noticed can differ.
- A replay only covers the states that occurred in the recording. A different
  architecture produces different states, so it needs its own recording (Step 9
  records each configuration once).

## Run it

```bash
python -m scripts.step6_replay                                   # synthetic demo, no key
python -m scripts.step6_replay --record --name jev-oct --games 5 # live, ~150 requests
python -m scripts.step6_replay --name jev-oct --games 5          # replay
```
