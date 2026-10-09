"""Step 9: the full sweep, architecture x deadline x skill x repetition, into one dataset.

Offline (simulated Jev, seconds):
    python -m scripts.step9_run_experiments

With your measured latencies:
    python -m scripts.step9_run_experiments --latency results/step0/jev_latency.csv

With the real Jev's decisions (two runs: record once, then replay for the final data):
    python -m scripts.step9_run_experiments --latency results/step0/jev_latency.csv \\
        --answers record:data/recordings/sweep/answers.json --workers 8
    python -m scripts.step9_run_experiments --latency results/step0/jev_latency.csv \\
        --answers replay:data/recordings/sweep/answers.json

Writes results/step9/dataset.csv (one row per game) and meta.json.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from framebudget.experiment import ARCHS, Setup, cells
from framebudget.game import SKILLS
from framebudget.jev import PRICE_PER_M_INPUT_TOKENS
from framebudget.sim import run_episode


def build_answers(spec: str):
    if spec == "fake":
        return "fake", None
    from framebudget.replay import AnswerStore, LiveAnswers, StoreAnswers

    mode, _, path = spec.partition(":")
    store = AnswerStore(path)
    if mode == "replay":
        return StoreAnswers(store), store
    if mode == "record":
        from framebudget.jev import load_api_key

        return StoreAnswers(store, fallback=LiveAnswers(load_api_key())), store
    raise SystemExit("--answers must be fake, record:<path> or replay:<path>")


def run_cell(setup: Setup, cell) -> dict:
    name, budget, skill, seed = cell
    r = run_episode(setup.arch(name, budget, skill, seed), skill, seed)
    row = r.row()
    row["arch"] = name
    row["budget_ms"] = budget if budget is not None else float("nan")
    row["tokens_total"] = row["input_tokens"] + row.get("prefetch_tokens", 0)
    row["requests_total"] = row["requests"] + row.get("prefetch_requests", 0)
    row["cost_usd"] = row["tokens_total"] * PRICE_PER_M_INPUT_TOKENS / 1e6
    row["cost_per_hour_usd"] = row["cost_usd"] / max(row["duration_s"], 1e-9) * 3600
    row["requests_per_hour"] = row["requests_total"] / max(row["duration_s"], 1e-9) * 3600
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=30, help="games per (architecture, deadline, skill)")
    ap.add_argument("--archs", default=",".join(ARCHS))
    ap.add_argument("--budgets", default="33,100,250,500")
    ap.add_argument("--coarse", type=float, default=1.0)
    ap.add_argument("--latency", default="synthetic")
    ap.add_argument("--answers", default="fake", help="fake | record:<answers.json> | replay:<answers.json>")
    ap.add_argument("--workers", type=int, default=1, help="parallel games (useful when recording live)")
    ap.add_argument("--out", default="results/step9")
    args = ap.parse_args()

    answers, store = build_answers(args.answers)
    setup = Setup(answers, args.latency, args.coarse)
    todo = list(cells(args.archs.split(","), [float(b) for b in args.budgets.split(",")],
                      list(SKILLS), args.reps))
    print(f"{len(todo)} games ...", flush=True)
    t0 = time.time()
    if args.workers > 1:
        with ThreadPoolExecutor(args.workers) as pool:
            futures = [pool.submit(run_cell, setup, c) for c in todo]
            for i, _ in enumerate(as_completed(futures), 1):
                if i % 100 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
                    if store is not None:
                        store.save()  # an interrupted record run keeps what it has
            rows = [f.result() for f in futures]  # in design order, whatever finished first
    else:
        rows = []
        for i, c in enumerate(todo, 1):
            rows.append(run_cell(setup, c))
            if i % 200 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
                if store is not None:
                    store.save()
    if store is not None:
        store.save()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).fillna({"prefetch_requests": 0, "prefetch_used": 0, "prefetch_tokens": 0})
    df.to_csv(out / "dataset.csv", index=False)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    meta = {**vars(args), "games": len(df), "seconds": round(time.time() - t0, 1),
            "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git_commit": commit}
    if store is not None:
        meta["answers_in_store"] = len(store)
        meta["store_hits"], meta["store_misses"] = answers.hits, answers.misses
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote {len(df)} rows to {out / 'dataset.csv'} in {meta['seconds']} s")
    print(df.groupby(["arch", "budget_ms"], dropna=False)[["deadline_met", "fallback_rate", "died"]]
          .mean().round(3).to_string())


if __name__ == "__main__":
    main()
