"""Step 4: the blocking architecture. How badly does waiting for Jev break the tick?

    python -m scripts.step4_blocking                       # simulated Jev, simulated clock
    python -m scripts.step4_blocking --latency results/step0/jev_latency.csv
    python -m scripts.step4_blocking --live                # real Jev, real clock (needs key)

The simulated version runs 50 games per skill in seconds. --live plays one game
per skill in real time (about 1.5 to 2 minutes each) against the real Jev.
Writes results/step4/: games.csv, summary.md, tick_timeline.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from framebudget.arch import Blocking, RulesOnly
from framebudget.clock import RealClock, SimClock
from framebudget.deciders import FakeAnswers, LiveJevDecider, SimulatedJev
from framebudget.game import SKILLS
from framebudget.latency import latency_model
from framebudget.loop import TICK_S
from framebudget.sim import run_episode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=50)
    ap.add_argument("--latency", default="synthetic", help="'synthetic' or a Step 0 CSV")
    ap.add_argument("--live", action="store_true", help="real Jev on the real clock")
    ap.add_argument("--out", default="results/step4")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.live:
        from framebudget.jev import JevClient, load_api_key

        key = load_api_key()
        games = 1
        make = lambda seed: Blocking(LiveJevDecider(JevClient(key)))
        clock = RealClock
    else:
        games = args.games
        make = lambda seed: Blocking(SimulatedJev(FakeAnswers(seed), latency_model(args.latency, seed)))
        clock = SimClock

    rows, timeline = [], None
    for skill in SKILLS:
        for seed in range(games):
            if args.live:
                print(f"live game, {skill} bot ...", flush=True)
            r = run_episode(make(seed), skill, seed, clock=clock(), keep_ticks=timeline is None)
            rows.append({**r.row(), "tick_p50_ms": r.ticks["period_p50_ms"],
                         "blowout_factor": r.ticks["blowout_factor"]})
            if timeline is None:
                timeline = r
        # the same games under rules only, as the "no model" reference
        for seed in range(games):
            r = run_episode(RulesOnly(), skill, seed, clock=SimClock())
            rows.append({**r.row(), "tick_p50_ms": r.ticks["period_p50_ms"],
                         "blowout_factor": r.ticks["blowout_factor"]})
    df = pd.DataFrame(rows)
    df.to_csv(out / "games.csv", index=False)

    b = df[df.arch == "blocking"]
    s = df.groupby("arch").agg(
        games=("seed", "size"), tick_p99_ms=("tick_p99_ms", "mean"), tick_max_ms=("tick_max_ms", "max"),
        blowout_mean=("blowout_factor", "mean"), blowout_max=("blowout_factor", "max"),
        overruns_per_game=("overruns", "mean"),
    ).round(2)
    mode = "LIVE Jev, real clock" if args.live else f"simulated Jev, latency={args.latency}"
    (out / "summary.md").write_text(
        f"# Step 4: blocking architecture ({mode})\n\n" + s.to_markdown() + "\n\n"
        f"Budget per tick: {TICK_S*1000:.0f} ms. Every decision point in a blocking game is an "
        f"overrun: {b.overruns.sum()} overruns in {b.decisions.sum()} decisions.\n\n"
        f"**Blowout factor** = longest tick / 33 ms. Mean over games: {b.blowout_factor.mean():.1f}x, "
        f"worst game: {b.blowout_factor.max():.1f}x.\n"
    )
    print((out / "summary.md").read_text())

    # Tick timeline of one game: one spike per decision point.
    periods = timeline.tick_periods_ms
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(periods, lw=0.7, color="#d1495b")
    ax.axhline(TICK_S * 1000, color="#555", ls="--", lw=1, label="33 ms budget")
    ax.set(xlabel="tick", ylabel="tick period (ms)",
           title=f"Blocking, one game ({timeline.skill} bot): every decision freezes the loop")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "tick_timeline.png", dpi=150)


if __name__ == "__main__":
    main()
