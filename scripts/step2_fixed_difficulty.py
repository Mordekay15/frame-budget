"""Step 2: the game at fixed difficulty, for each bot skill.

    python -m scripts.step2_fixed_difficulty            # 200 games per skill
    python -m scripts.step2_fixed_difficulty --games 50

Every wave has 5 enemies at damage x1.0. Expected outcome: the weak bot dies,
the medium bot mostly survives with real pressure, the strong bot is bored.
Writes results/step2/: games.csv, summary.md, health_traces.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from framebudget.game import DEFAULT_DECISION, SKILLS
from framebudget.sim import FixedDifficulty, run_episode

COLORS = {"weak": "#d1495b", "medium": "#edae49", "strong": "#00798c"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--out", default="results/step2")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows, traces = [], {}
    for skill in SKILLS:
        for seed in range(args.games):
            arch = FixedDifficulty(DEFAULT_DECISION)
            r = run_episode(arch, skill, seed)
            rows.append(r.row())
            if seed < 5:
                traces.setdefault(skill, []).append(r)
    df = pd.DataFrame(rows)
    df.to_csv(out / "games.csv", index=False)

    summary = df.groupby("skill", sort=False).agg(
        games=("died", "size"), death_rate=("died", "mean"), waves=("waves_cleared", "mean"),
        bored=("bored", "mean"), in_band=("in_band", "mean"), danger=("danger", "mean"),
        mean_health=("mean_health", "mean"),
    ).round(3)
    (out / "summary.md").write_text(
        "# Step 2: fixed difficulty (5 enemies, damage x1.0)\n\n"
        + summary.to_markdown() + "\n\n"
        "bored = share of time with health >= 90%, danger = <= 20%, in_band = the rest.\n"
    )
    print((out / "summary.md").read_text())

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    for ax, (skill, rs) in zip(axes, traces.items()):
        for r in rs:
            h = [w.health_after for w in r.waves]
            ax.plot(range(1, len(h) + 1), h, color=COLORS[skill], alpha=0.7)
        ax.set(title=f"{skill} bot", xlabel="wave")
        ax.axhspan(90, 100, color="#ccc", alpha=0.4)
        ax.axhspan(0, 20, color="#f4b6b6", alpha=0.4)
    axes[0].set_ylabel("health after wave")
    fig.suptitle("Fixed difficulty: 5 games per skill (grey = bored zone, red = danger zone)")
    fig.tight_layout()
    fig.savefig(out / "health_traces.png", dpi=150)


if __name__ == "__main__":
    main()
