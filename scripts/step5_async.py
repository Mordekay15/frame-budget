"""Step 5: asynchronous requests with a rules fallback.

    python -m scripts.step5_async                          # simulated, all budgets, 50 games each
    python -m scripts.step5_async --latency results/step0/jev_latency.csv
    python -m scripts.step5_async --real-clock --budgets 100 --games 1
                                                           # threads + real time, simulated Jev
    python -m scripts.step5_async --live --budgets 250     # threads + real time + real Jev

Writes results/step5/: games.csv, summary.md, deadline_vs_budget.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from framebudget.arch import AsyncFallback
from framebudget.channel import SimChannel, ThreadChannel
from framebudget.clock import RealClock, SimClock
from framebudget.deciders import FakeAnswers, LiveJevDecider, SimulatedJev
from framebudget.game import SKILLS
from framebudget.latency import latency_model
from framebudget.sim import run_episode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=50)
    ap.add_argument("--budgets", default="33,100,250,500")
    ap.add_argument("--latency", default="synthetic")
    ap.add_argument("--real-clock", action="store_true", help="real time and worker threads")
    ap.add_argument("--live", action="store_true", help="real Jev (implies --real-clock)")
    ap.add_argument("--out", default="results/step5")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    budgets = [float(b) for b in args.budgets.split(",")]
    real = args.real_clock or args.live
    if args.live:
        from framebudget.jev import JevClient, load_api_key

        key = load_api_key()

    def make(budget: float, seed: int, clock):
        if args.live:
            ch = ThreadChannel(lambda: LiveJevDecider(JevClient(key)), clock)
        elif real:
            ch = ThreadChannel(lambda: SimulatedJev(FakeAnswers(seed), latency_model(args.latency, seed)), clock)
        else:
            ch = SimChannel(SimulatedJev(FakeAnswers(seed), latency_model(args.latency, seed)))
        return AsyncFallback(ch, budget)

    rows = []
    for budget in budgets:
        for skill in SKILLS:
            for seed in range(args.games):
                clock = RealClock() if real else SimClock()
                if real:
                    print(f"budget {budget:.0f} ms, {skill} bot, game {seed} (real time) ...", flush=True)
                r = run_episode(make(budget, seed, clock), skill, seed, clock=clock)
                rows.append(r.row())
    df = pd.DataFrame(rows)
    df.to_csv(out / "games.csv", index=False)

    s = df.groupby("budget_ms").agg(
        games=("seed", "size"), deadline_met=("deadline_met", "mean"),
        fallback_rate=("fallback_rate", "mean"), late=("late", "sum"), stale=("stale", "sum"),
        failed=("failed", "sum"), tick_p99_ms=("tick_p99_ms", "mean"), tick_max_ms=("tick_max_ms", "max"),
        overruns=("overruns", "sum"), death_rate=("died", "mean"),
    ).round(3)
    mode = "LIVE Jev, real clock" if args.live else ("simulated Jev, real clock" if real else "simulated Jev and clock")
    (out / "summary.md").write_text(
        f"# Step 5: async with rules fallback ({mode}, latency={args.latency})\n\n"
        + s.to_markdown() + "\n\n"
        "deadline_met: share of decisions where Jev's answer arrived within the budget and was used.\n"
        "fallback_rate: share where the rules decided instead. late/stale/failed: discarded answers.\n"
        "tick_max_ms is the longest tick: it stays at the 33 ms budget (on the simulated clock exactly,\n"
        "on the real clock within the jitter measured in Step 1).\n"
    )
    print((out / "summary.md").read_text())

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(s.index, s.deadline_met, "o-", color="#2a6fdb", label="Jev answer used (in time)")
    ax.plot(s.index, s.fallback_rate, "s--", color="#999", label="rules fallback")
    ax.set(xlabel="decision deadline (ms)", ylabel="share of decisions", ylim=(0, 1),
           title="Async + fallback: who decided?")
    ax.set_xticks(s.index)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "deadline_vs_budget.png", dpi=150)


if __name__ == "__main__":
    main()
