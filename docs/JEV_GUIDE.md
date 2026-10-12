# Working with Jev: step by step

This guide takes you from "I have access to Jev" to real measurements in the repo.
You only need to do parts 1 to 3 once.

## What Jev is, in two sentences

Jev is a *decision* model: you send it a description of a situation (`state`) and
typed questions, and it answers each question with a choice plus probabilities.
It does not write text, which is why it is much faster than a chat model.

Our request looks like this (see `framebudget/jev.py`):

```json
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <your TypeSafe key>

{
  "model": "jev-1.13.0",
  "state": "Action game, difficulty tuning. Player health: 35 of 100. Wave 6 was just cleared. ...",
  "questions": {
    "enemy_count": {"type": "choice", "instructions": "How many enemies should the next wave contain?",
                    "criteria": {"enemies_3": "3 enemies: ...", "enemies_5": "...", "enemies_8": "...", "enemies_12": "..."}},
    "damage_mult": {"type": "choice", "instructions": "How hard should the enemies hit?",
                    "criteria": {"soft": "0.75x", "normal": "1x", "hard": "1.25x", "brutal": "1.5x"}}
  }
}
```

and the answer:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "enemy_count": {"type": "choice", "choice": "enemies_3", "confidence": 0.71,
                    "probabilities": {"enemies_3": 0.71, "enemies_5": 0.22, "enemies_8": 0.05, "enemies_12": 0.02}},
    "damage_mult": {"type": "choice", "choice": "soft", "confidence": 0.64, "probabilities": {"...": 0.0}}
  },
  "usage": {"input_tokens": 251, "output_tokens": 0}
}
```

(The numbers above are illustrative; `scripts/jev_hello.py` shows you a real one.)

The code also works with Jev through OpenRouter (different address, same request).
It picks whichever key you put in `.env`; this guide assumes a TypeSafe key.

## 1. Get an API key

1. Sign in at https://console.typesafe.ai.
2. Open **Keys** (https://console.typesafe.ai/keys) and create a key, for example
   named `thesis`. Copy it right away; you may not be able to see it again.
3. Jev costs $0.042 per million input tokens (output is free), so the whole
   thesis costs well under a dollar. If the console asks for billing or credit,
   set that up there.

## 2. Get the code onto your laptop

You need Python 3.10 or newer (`python3 --version`) and git.

```bash
git clone https://github.com/Mordekay15/frame-budget.git
cd frame-budget
git checkout step-0          # or the step you want to run, e.g. step-10 has everything
```

Create a virtual environment (a private folder of libraries for this project) and
install the analysis libraries:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Every time you open a new terminal, run the `activate` line again.

## 3. Put the key in a `.env` file

```bash
cp .env.example .env               # Windows: copy .env.example .env
```

Open `.env` in an editor and replace the placeholder with your key:

```
TYPESAFE_API_KEY=...your key...
```

`.env` is listed in `.gitignore`, so git will never upload it. Never paste the key
into a code file or a chat.

## 4. First call

```bash
python -m scripts.jev_hello
```

You should see the state that was sent, `HTTP 200`, Jev's full JSON answer and
the latency of a second request. Typical problems:

| You see | Meaning | Fix |
|---|---|---|
| `No API key` | `.env` missing or misnamed | Check the file is called exactly `.env` and is in the repo root |
| `HTTP 401` | key wrong or revoked | Create a new key, paste it again |
| `HTTP 402` / `403` | no credit or no access | Check billing in the TypeSafe console |
| `HTTP 404` / unknown model | model name changed | Check https://docs.typesafe.ai/models and update `"model"` under `typesafe` in `PROVIDERS` in `framebudget/jev.py` |
| `HTTP 429` | rate limit (80 requests per second) | Wait a moment; only possible with many parallel workers |
| `unexpected answer shape` | API format changed | Send me the JSON that `jev_hello` printed |

## 5. Step 0: measure the latency

```bash
python -m scripts.step0_measure_latency
```

This sends 431 requests (300 warm, 100 cold, 30 same-state, one warm-up) with a
200 ms pause between them and takes about 3 minutes. It writes a new file
`results/step0/jev_latency_<date>_<time>.csv` row by row, so an interruption
loses nothing and a second run never overwrites the first.

**Run it several times, at different times of day** (for example morning,
afternoon and evening, ideally on two different days). Jev's latency is not
constant: on 12 Oct the median was 310 ms at 12:24 but 238 ms half an hour
later. Every later step pools all runs it finds in `results/step0/`, so the
simulation uses a mix of good and bad moments instead of one random snapshot.

Close other downloads and video calls while it runs; they add latency. Write
down where you ran it (home Wi-Fi, university network, ...), since that belongs
in the methodology chapter.

Then:

```bash
python -m scripts.step0_analyze "results/step0/jev_latency*.csv"
```

The quotes matter: they let the script find all runs itself. It prints the
pooled table, a per-run comparison, and writes `summary.md`, `latency_hist.png` and
`latency_ecdf.png` into `results/step0/`.

## 6. Save the results to GitHub

```bash
git add results/step0
git commit -m "Step 0: real Jev latency measurements"
git push
```

Once the CSV is on GitHub I can read it and the later steps use it as the
latency recording (see Step 6).

## 7. Everything that talks to Jev, in order

Run these from the repo root on branch `step-10` (it contains all steps), with
the virtual environment active. Commit `results/` and `data/recordings/` after each one.

| # | command | what it does | requests | time |
|---|---|---|---|---|
| 1 | `python -m scripts.jev_hello` | first call, checks key and format | 2 | seconds |
| 2 | `python -m scripts.step0_measure_latency` (3 or more times, spread over the day) then `python -m scripts.step0_analyze "results/step0/jev_latency*.csv"` | the latency distribution | 431 per run | ~3 min per run |
| 3 | `python -m scripts.step1_bare_loop` | loop timing on your machine (no Jev) | 0 | ~6 min |
| 4 | `python -m scripts.step4_blocking --live` | blocking with the real Jev, real clock | ~90 | ~5 min |
| 5 | `python -m scripts.step5_async --live --budgets 250 --games 1` | async with real threads and real Jev | ~90 | ~5 min |
| 6 | `python -m scripts.step6_replay --record --name jev-oct --games 5` then `python -m scripts.step6_replay --name jev-oct --games 5` | record, then prove identical replay | ~450 | ~3 min |
| 7 | see below | the full sweep with Jev's real decisions | ~54 000 | ~35 min with 8 workers |
| 8 | `python -m scripts.step9_consistency --live` | consistency of the real Jev | 360 | ~2 min |
| 9 | `python -m scripts.step10_analyze` | tables and figures | 0 | seconds |

**Step 7 (the sweep)** in two runs. The first asks the live Jev for every
decision and stores the answers; the second replays them, which gives the final,
reproducible dataset:

macOS / Linux (bash):

```bash
L="results/step0/jev_latency*.csv"   # all Step 0 runs, pooled
python -m scripts.step9_run_experiments --latency "$L" --answers record:data/recordings/sweep/answers.json --workers 8
python -m scripts.step9_run_experiments --latency "$L" --answers replay:data/recordings/sweep/answers.json
python -m scripts.step10_analyze
```

Windows (PowerShell):

```powershell
$L = "results/step0/jev_latency*.csv"   # all Step 0 runs, pooled
python -m scripts.step9_run_experiments --latency "$L" --answers record:data/recordings/sweep/answers.json --workers 8
python -m scripts.step9_run_experiments --latency "$L" --answers replay:data/recordings/sweep/answers.json
python -m scripts.step10_analyze
```

At 646 input tokens per request (measured with `jev_hello`), 54 000 requests cost about $1.50. Start
with `--reps 3` to check that everything works (about 5 400 requests). If the
record run is interrupted, just start it again: answers already stored are
reused, not requested again.

All offline versions (no flags, or without `--live`) use the simulated Jev and
run without a key, so you can always try a command offline first.
