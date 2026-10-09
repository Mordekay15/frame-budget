# Working with Jev: step by step

This guide takes you from "I have access to Jev" to real measurements in the repo.
You only need to do parts 1 to 3 once.

## What Jev is, in two sentences

Jev is a *decision* model: you send it a description of a situation (`state`) and
typed questions, and it answers each question with a choice plus probabilities.
It does not write text, which is why it is much faster than a chat model.

Our request looks like this (see `framebudget/jev.py`):

```json
POST https://openrouter.ai/api/alpha/decisions
Authorization: Bearer sk-or-v1-...

{
  "model": "typesafe/jev-1.13",
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
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "enemy_count": {"type": "choice", "choice": "enemies_3", "confidence": 0.71,
                    "probabilities": {"enemies_3": 0.71, "enemies_5": 0.22, "enemies_8": 0.05, "enemies_12": 0.02}},
    "damage_mult": {"type": "choice", "choice": "soft", "confidence": 0.64, "probabilities": {"...": 0.0}}
  },
  "usage": {"input_tokens": 251, "output_tokens": 0, "cost": 0.0000105}
}
```

(The numbers above are illustrative; `scripts/jev_hello.py` shows you a real one.)

## 1. Get an API key

1. Sign in at https://openrouter.ai.
2. Jev is paid per token (about $0.04 per million input tokens, so the whole
   thesis costs cents). Add a small amount of credit under **Settings > Credits**
   if your account has none; $5 is far more than enough.
3. Go to **Settings > Keys** (https://openrouter.ai/settings/keys), press
   **Create Key**, name it `thesis`, and copy the key. It starts with `sk-or-v1-`.
   You can only see it once, so paste it somewhere safe right away.

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
OPENROUTER_API_KEY=sk-or-v1-...your key...
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
| `HTTP 402` | no credit | Add credit on OpenRouter |
| `HTTP 404` / unknown model | model name changed | Check https://openrouter.ai/typesafe and update `MODEL` in `framebudget/jev.py` |
| `unexpected answer shape` | API format changed | Send me the JSON that `jev_hello` printed |

## 5. Step 0: measure the latency

```bash
python -m scripts.step0_measure_latency
```

This sends 431 requests (300 warm, 100 cold, 30 same-state, one warm-up) with a
200 ms pause between them and takes about 3 minutes. It writes
`results/step0/jev_latency.csv` row by row, so an interruption loses nothing.

Close other downloads and video calls while it runs; they add latency. Write
down where you ran it (home Wi-Fi, university network, ...), since that belongs
in the methodology chapter.

Then:

```bash
python -m scripts.step0_analyze results/step0/jev_latency.csv
```

This prints a table and writes `summary.md`, `latency_hist.png` and
`latency_ecdf.png` into `results/step0/`.

## 6. Save the results to GitHub

```bash
git add results/step0
git commit -m "Step 0: real Jev latency measurements"
git push
```

Once the CSV is on GitHub I can read it and the later steps use it as the
latency recording (see Step 6).
