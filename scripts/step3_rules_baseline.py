"""Step 3: Hunicke's comfort-zone policy vs fixed difficulty.

    python -m scripts.step3_rules_baseline            # 200 games per skill and policy

Writes results/step3/: games.csv, summary.md, shift.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from framebudget.arch import RulesOnly
from framebudget.game import DEFAULT_DECISION, SKILLS
from framebudget.sim import FixedDifficulty, run_episode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--out", default="results/step3")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    makers = {"fixed": lambda: FixedDifficulty(DEFAULT_DECISION), "rules": RulesOnly}
    rows = []
    for skill in SKILLS:
        for name, make in makers.items():
            for seed in range(args.games):
                rows.append(run_episode(make(), skill, seed).row())
    df = pd.DataFrame(rows)
    df.to_csv(out / "games.csv", index=False)

    s = df.groupby(["skill", "arch"], sort=False).agg(
        death_rate=("died", "mean"), waves=("waves_cleared", "mean"),
        bored=("bored", "mean"), in_band=("in_band", "mean"), danger=("danger", "mean"),
    ).round(3)
    shift = (s.xs("rules", level="arch") - s.xs("fixed", level="arch")).round(3)
    (out / "summary.md").write_text(
        "# Step 3: rules (Hunicke comfort zone) vs fixed difficulty\n\n"
        f"{args.games} games per skill and policy, same seeds for both policies.\n\n"
        + s.to_markdown() + "\n\n## Shift (rules minus fixed)\n\n" + shift.to_markdown() + "\n"
    )
    print((out / "summary.md").read_text())

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, metric in zip(axes, ["death_rate", "bored", "in_band"]):
        piv = s[metric].unstack("arch").reindex(list(SKILLS))
        piv.plot.bar(ax=ax, color={"fixed": "#999999", "rules": "#2a6fdb"}, rot=0)
        ax.set(title=metric.replace("_", " "), xlabel="")
        ax.set_ylim(0, 1)
    fig.suptitle("Effect of difficulty adjustment (rules) compared with fixed difficulty")
    fig.tight_layout()
    fig.savefig(out / "shift.png", dpi=150)


if __name__ == "__main__":
    main()
