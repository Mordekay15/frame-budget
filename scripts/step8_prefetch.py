"""Step 8: predictive prefetch against plain async and cache.

    python -m scripts.step8_prefetch
    python -m scripts.step8_prefetch --latency results/step0/jev_latency.csv

Every game starts with an empty cache (coarseness 1), so all the benefit of
cache and prefetch here comes from within one game.
Writes results/step8/: games.csv, summary.md, prefetch.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from framebudget.arch import AsyncFallback, CachedAsync, PrefetchAsync
from framebudget.channel import SimChannel
from framebudget.deciders import FakeAnswers, SimulatedJev
from framebudget.game import SKILLS
from framebudget.latency import latency_model
from framebudget.sim import run_episode

COLORS = {"async": "#999999", "cache": "#2a6fdb", "prefetch": "#d1495b"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--budgets", default="33,100,250,500")
    ap.add_argument("--coarse", type=float, default=1.0)
    ap.add_argument("--latency", default="synthetic")
    ap.add_argument("--out", default="results/step8")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    archs = {
        "async": lambda ch, b: AsyncFallback(ch, b),
        "cache": lambda ch, b: CachedAsync(ch, b, coarse=args.coarse),
        "prefetch": lambda ch, b: PrefetchAsync(ch, b, coarse=args.coarse),
    }
    rows = []
    for budget in map(float, args.budgets.split(",")):
        for name, make in archs.items():
            for skill in SKILLS:
                for seed in range(args.games):
                    jev = SimulatedJev(FakeAnswers(seed), latency_model(args.latency, seed))
                    rows.append(run_episode(make(SimChannel(jev), budget), skill, seed).row())
    df = pd.DataFrame(rows).fillna(0)
    df.to_csv(out / "games.csv", index=False)

    df["all_requests"] = df.requests + df.get("prefetch_requests", 0)
    s = df.groupby(["budget_ms", "arch"], sort=False).agg(
        deadline_met=("deadline_met", "mean"), fallback_rate=("fallback_rate", "mean"),
        cache_hit_rate=("cache_hit_rate", "mean"), requests_per_game=("all_requests", "mean"),
        prefetch_per_game=("prefetch_requests", "mean"), prefetch_used=("prefetch_used", "mean"),
        death_rate=("died", "mean"),
    ).round(3)
    (out / "summary.md").write_text(
        f"# Step 8: prefetch vs cache vs async (coarseness {args.coarse:g}, latency={args.latency})\n\n"
        f"{args.games} games per skill, cache emptied for every game.\n\n" + s.to_markdown() + "\n\n"
        "prefetch_used: prefetched signatures that a real decision point later hit (per game).\n"
    )
    print((out / "summary.md").read_text())

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for name in archs:
        sub = s.xs(name, level="arch")
        axes[0].plot(sub.index, sub.deadline_met, "o-", color=COLORS[name], label=name)
        axes[1].plot(sub.index, sub.requests_per_game, "o-", color=COLORS[name], label=name)
    axes[0].set(xlabel="deadline (ms)", ylabel="decisions by the model, in time", ylim=(0, 1),
                title="Who decides")
    axes[1].set(xlabel="deadline (ms)", ylabel="requests per game", title="What it costs")
    for ax in axes:
        ax.set_xticks(list(s.index.get_level_values(0).unique()))
        ax.legend()
    fig.tight_layout()
    fig.savefig(out / "prefetch.png", dpi=150)


if __name__ == "__main__":
    main()
