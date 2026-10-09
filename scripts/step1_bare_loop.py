"""Step 1: the bare loop. Ticks that do nothing but count, timed for real.

    python -m scripts.step1_bare_loop            # 10 000 ticks, about 5.5 minutes
    python -m scripts.step1_bare_loop --ticks 1000

Writes ticks.csv, summary.md, tick_hist.png and drift.png to results/step1/.
Run it on the machine you will use for the experiments, with nothing heavy open.
"""

from __future__ import annotations

import argparse
import csv
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from framebudget.clock import RealClock
from framebudget.loop import TICK_S, run_loop, tick_summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=10_000)
    ap.add_argument("--out", default="results/step1")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    count = 0

    def tick(i: int) -> None:
        nonlocal count
        count += 1

    print(f"Running {args.ticks} ticks of {TICK_S * 1000:.0f} ms (~{args.ticks * TICK_S / 60:.1f} min)...")
    recs = run_loop(tick, RealClock(), n_ticks=args.ticks)
    s = tick_summary(recs)

    with (out / "ticks.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i", "scheduled_ms", "started_ms", "lateness_ms", "work_ms", "period_ms"])
        for r in recs:
            w.writerow([r.i, f"{r.scheduled*1000:.4f}", f"{r.started*1000:.4f}",
                        f"{r.lateness*1000:.4f}", f"{r.work*1000:.4f}", f"{r.period*1000:.4f}"])

    lines = [
        "# Step 1: bare loop\n",
        f"Machine: {platform.platform()}, Python {sys.version.split()[0]}\n",
        "| metric | value |", "|---|---|",
        *(f"| {k} | {v:.4f} |" if isinstance(v, float) else f"| {k} | {v} |" for k, v in s.items()),
        "\n`final_drift_ms` is how far the last tick started from its schedule. With an absolute",
        "schedule it stays bounded instead of growing with the number of ticks.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n")

    periods = [r.period * 1000 for r in recs[1:]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(periods, bins=100, color="#2a6fdb")
    ax.axvline(TICK_S * 1000, color="#555", ls="--", lw=1)
    ax.set_yscale("log")
    ax.set(xlabel="tick period (ms)", ylabel="ticks (log scale)",
           title=f"Bare loop: {len(recs)} ticks at {TICK_S*1000:.0f} ms")
    fig.tight_layout()
    fig.savefig(out / "tick_hist.png", dpi=150)

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot([r.i for r in recs], [r.lateness * 1000 for r in recs], lw=0.6, color="#e07b39")
    ax.set(xlabel="tick", ylabel="start lateness (ms)", title="Drift: actual start minus scheduled start")
    fig.tight_layout()
    fig.savefig(out / "drift.png", dpi=150)

    print((out / "summary.md").read_text())


if __name__ == "__main__":
    main()
