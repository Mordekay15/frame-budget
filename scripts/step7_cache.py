"""Step 7: cache hit rate (and its price) against discretisation coarseness.

    python -m scripts.step7_cache
    python -m scripts.step7_cache --latency results/step0/jev_latency.csv

For each coarseness c, one cache is shared by all games (all skills, played in
turn), as a cache on a game server would be. Deadline 250 ms.
`mismatch` = share of cache hits where a noise-free decider would have chosen a
different decision for the exact state: the cost of coarse buckets.
Writes results/step7/: games.csv, summary.md, hit_rate_vs_coarseness.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from framebudget.arch import CachedAsync
from framebudget.channel import SimChannel
from framebudget.deciders import FakeAnswers, SimulatedJev
from framebudget.game import SKILLS
from framebudget.latency import latency_model
from framebudget.sim import run_episode

LEVELS = (0.25, 0.5, 1, 2, 4, 8)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=30, help="games per skill and coarseness")
    ap.add_argument("--budget", type=float, default=250)
    ap.add_argument("--latency", default="synthetic")
    ap.add_argument("--out", default="results/step7")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for c in LEVELS:
        cache: dict = {}
        oracle = FakeAnswers(noise=0)
        for seed in range(args.games):
            for skill in SKILLS:
                # Noise-free answers, so `mismatch` measures only what the buckets throw away.
                jev = SimulatedJev(FakeAnswers(seed, noise=0), latency_model(args.latency, seed))
                arch = CachedAsync(SimChannel(jev), args.budget, coarse=c, cache=cache, oracle=oracle)
                r = run_episode(arch, skill, seed)
                rows.append({**r.row(), "coarse": c, "order": seed})
    df = pd.DataFrame(rows)
    df.to_csv(out / "games.csv", index=False)

    g = df.groupby("coarse")
    s = pd.DataFrame({
        "hit_rate": g.hits.sum() / (g.hits.sum() + g.misses.sum()),
        "mismatch": g.mismatches.sum() / g.hits.sum().clip(lower=1),
        "deadline_met": g.deadline_met.mean(),
        "fallback_rate": g.fallback_rate.mean(),
        "requests_per_game": g.requests.mean(),
        "cache_size": g.cache_size.max(),
        "death_rate": g.died.mean(),
    }).round(3)
    late = df[df.order >= args.games // 2].groupby("coarse")
    s["hit_rate_2nd_half"] = (late.hits.sum() / (late.hits.sum() + late.misses.sum())).round(3)
    (out / "summary.md").write_text(
        f"# Step 7: cached decisions (deadline {args.budget:.0f} ms, latency={args.latency})\n\n"
        f"{args.games} games per skill and coarseness; one shared cache per coarseness.\n\n"
        + s.to_markdown() + "\n\n"
        "hit_rate_2nd_half: hit rate once the cache has warmed up (second half of the games).\n"
        "mismatch: share of hits where a noise-free decider would choose differently for the exact state.\n"
    )
    print((out / "summary.md").read_text())

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(s.index, s.hit_rate, "o-", color="#2a6fdb", label="cache hit rate")
    ax.plot(s.index, s.mismatch, "s--", color="#d1495b", label="hits with a different decision than exact state")
    ax.plot(s.index, s.deadline_met, "^-", color="#4c9f70", label="decisions by Jev or cache in time")
    ax.set_xscale("log", base=2)
    ax.set_xticks(list(s.index))
    ax.set_xticklabels([f"{c:g}" for c in s.index])
    ax.set(xlabel="coarseness c (health bucket = 10c)", ylabel="share", ylim=(0, 1),
           title="Cache: hit rate against discretisation")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "hit_rate_vs_coarseness.png", dpi=150)


if __name__ == "__main__":
    main()
