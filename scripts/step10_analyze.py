"""Step 10: analysis and figures for the results chapter.

    python -m scripts.step10_analyze
    python -m scripts.step10_analyze --dataset results/step9/dataset.csv \\
        --consistency results/step9/consistency.csv --out results/step10

Writes into results/step10/:
  main_table.md / main_table.tex      architecture x deadline, the four metrics
  experience_table.md                 death rate, in-band and bored time per skill
  fig_deadline.png                    metric 1: decisions by the model in time
  fig_fallback.png                    metric 2: rules fallback
  fig_consistency.png                 metric 3: agreement for identical input
  fig_cost.png                        metric 4: cost per hour of play
  fig_tick.png                        longest tick per architecture (why blocking is out)
  fig_experience.png                  death rate per skill and architecture
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# Fixed colour per architecture (validated categorical palette; colour follows
# the entity, so every figure uses the same mapping). Markers add a second cue.
STYLE = {
    "async": ("#2a78d6", "o"),
    "cache": ("#eb6834", "s"),
    "prefetch": ("#1baf7a", "^"),
    "blocking": ("#eda100", "D"),
    "rules": ("#6f6f6a", "x"),
}
ORDER = ["rules", "blocking", "async", "cache", "prefetch"]
SKILLS = ["weak", "medium", "strong"]

plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": "#e4e4e0", "grid.linewidth": 0.8, "axes.edgecolor": "#8a8a85",
    "axes.titlesize": 11, "axes.labelsize": 10, "legend.frameon": False,
    "lines.linewidth": 2, "lines.markersize": 7,
})


def ci95(x: pd.Series) -> float:
    """Half-width of a 95% confidence interval of the mean (normal approximation)."""
    n = x.count()
    return 1.96 * x.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")


def label(arch: str, budget) -> str:
    return arch if pd.isna(budget) else f"{arch} @ {budget:g} ms"


def main_table(df: pd.DataFrame, cons: pd.DataFrame | None) -> pd.DataFrame:
    g = df.groupby(["arch", "budget_ms"], dropna=False)
    t = pd.DataFrame({
        "games": g.size(),
        "deadline_met": g.deadline_met.mean(), "deadline_met_ci": g.deadline_met.agg(ci95),
        "fallback_rate": g.fallback_rate.mean(), "fallback_rate_ci": g.fallback_rate.agg(ci95),
        "cost_per_hour_usd": g.cost_per_hour_usd.mean(),
        "requests_per_hour": g.requests_per_hour.mean(),
        "tick_max_ms": g.tick_max_ms.max(),
    })
    if cons is not None:
        c = cons.groupby(["arch", "budget_ms"], dropna=False).agreement.mean()
        t["consistency"] = [c.get((a, b), float("nan")) if not pd.isna(b) else c.get((a, float("nan")),
                            c[c.index.get_level_values(0) == a].mean()) for a, b in t.index]
    t = t.reset_index()
    t["order"] = t.arch.map(ORDER.index)
    t = t.sort_values(["order", "budget_ms"]).drop(columns="order")
    # The rules make every decision themselves: deadline and fallback do not apply.
    t.loc[t.arch == "rules", ["deadline_met", "deadline_met_ci", "fallback_rate", "fallback_rate_ci"]] = float("nan")
    return t


def fmt_pct(m, ci) -> str:
    if pd.isna(m):
        return "n/a"
    return f"{m:.0%} ± {ci:.0%}" if not pd.isna(ci) else f"{m:.0%}"


def to_markdown(t: pd.DataFrame) -> str:
    rows = ["| architecture | deadline | model decided in time | rules fallback | consistency | cost / hour | requests / hour | longest tick |",
            "|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        rows.append(
            f"| {r.arch} | {'—' if pd.isna(r.budget_ms) else f'{r.budget_ms:g} ms'} | "
            f"{fmt_pct(r.deadline_met, r.deadline_met_ci)} | {fmt_pct(r.fallback_rate, r.fallback_rate_ci)} | "
            f"{'n/a' if pd.isna(r.get('consistency')) else f'{r.consistency:.2f}'} | "
            f"${r.cost_per_hour_usd:.4f} | {r.requests_per_hour:.0f} | {r.tick_max_ms:.0f} ms |")
    return "\n".join(rows)


def to_latex(t: pd.DataFrame) -> str:
    """A booktabs table, written by hand so no extra library is needed."""
    def pct(m, ci):
        return "--" if pd.isna(m) else (rf"{100*m:.0f}\,\% $\pm$ {100*ci:.0f}" if not pd.isna(ci) else rf"{100*m:.0f}\,\%")

    lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
             r"Architecture & Deadline & In time & Fallback & Consistency & Cost/h (USD) & Longest tick \\",
             r"\midrule"]
    for _, r in t.iterrows():
        lines.append(
            f"{r.arch} & {'--' if pd.isna(r.budget_ms) else f'{r.budget_ms:g} ms'} & "
            f"{pct(r.deadline_met, r.deadline_met_ci)} & {pct(r.fallback_rate, r.fallback_rate_ci)} & "
            f"{'--' if pd.isna(r.get('consistency')) else f'{r.consistency:.2f}'} & "
            f"{r.cost_per_hour_usd:.4f} & {r.tick_max_ms:.0f} ms \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def line_by_budget(df, col, ylabel, title, path, archs=("async", "cache", "prefetch"),
                   refs=(), ylim=(0, 1.02), fmt=None):
    fig, ax = plt.subplots(figsize=(6.4, 4))
    for a in archs:
        sub = df[df.arch == a].groupby("budget_ms")[col]
        m, e = sub.mean(), sub.agg(ci95)
        color, marker = STYLE[a]
        ax.errorbar(m.index, m.values, yerr=e.values, color=color, marker=marker, capsize=3, label=a)
    for a in refs:
        v = df[df.arch == a][col].mean()
        ax.axhline(v, color=STYLE[a][0], ls="--", lw=1.5, label=f"{a} (no deadline)")
    budgets = sorted(df.budget_ms.dropna().unique())
    ax.set_xscale("log")
    ax.set_xticks(budgets)
    ax.set_xticklabels([f"{b:g}" for b in budgets])
    ax.minorticks_off()
    ax.set(xlabel="decision deadline (ms, log scale)", ylabel=ylabel, title=title)
    if ylim:
        ax.set_ylim(*ylim)
    if fmt:
        ax.yaxis.set_major_formatter(fmt)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default="results/step9/dataset.csv")
    ap.add_argument("--consistency", default="results/step9/consistency.csv")
    ap.add_argument("--out", default="results/step10")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.dataset)
    cons = pd.read_csv(args.consistency) if Path(args.consistency).exists() else None
    t = main_table(df, cons)
    t.to_csv(out / "main_table.csv", index=False)
    (out / "main_table.md").write_text(
        f"# Architecture × deadline ({len(df)} games, `{args.dataset}`)\n\n" + to_markdown(t) + "\n\n"
        "± is the half-width of a 95% confidence interval over games. Consistency is the mean agreement\n"
        "for identical input (1.00 = always the same decision). Cost is input tokens × $0.042 per million,\n"
        "including prefetch requests. Longest tick is the worst single tick over all games.\n")
    (out / "main_table.tex").write_text(to_latex(t))

    exp = df.groupby(["arch", "budget_ms", "skill"], dropna=False).agg(
        death_rate=("died", "mean"), in_band=("in_band", "mean"), bored=("bored", "mean"),
        waves=("waves_cleared", "mean")).round(3).reset_index()
    exp["label"] = [label(a, b) for a, b in zip(exp.arch, exp.budget_ms)]
    piv = exp.pivot_table(index="label", columns="skill", values=["death_rate", "in_band", "bored"])
    piv = piv.reindex(columns=SKILLS, level=1)
    (out / "experience_table.md").write_text(
        "# How the games felt, per skill\n\n" + piv.round(2).to_markdown() + "\n")

    from matplotlib.ticker import PercentFormatter

    pct = PercentFormatter(1.0)
    line_by_budget(df, "deadline_met", "decisions made by the model in time",
                   "Metric 1: meeting the deadline", out / "fig_deadline.png", fmt=pct)
    line_by_budget(df, "fallback_rate", "decisions made by the rules instead",
                   "Metric 2: fallback to rules", out / "fig_fallback.png", fmt=pct)
    line_by_budget(df, "cost_per_hour_usd", "USD per hour of play",
                   "Metric 4: cost", out / "fig_cost.png", refs=("blocking",), ylim=None)
    if cons is not None:
        line_by_budget(cons, "agreement", "agreement for identical input",
                       "Metric 3: consistency", out / "fig_consistency.png",
                       refs=("rules", "blocking"), ylim=(0, 1.05))

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    tm = df.groupby("arch").tick_max_ms.max().reindex(ORDER)
    ax.barh(tm.index, tm.values, color=[STYLE[a][0] for a in tm.index], height=0.6)
    ax.axvline(33, color="#333", ls="--", lw=1)
    ax.text(33, -0.6, " 33 ms tick", fontsize=8, va="bottom")
    for y, v in enumerate(tm.values):
        ax.text(v, y, f" {v:.0f} ms", va="center", fontsize=9)
    ax.set_xlim(0, tm.max() * 1.18)
    ax.set(xlabel="longest tick over all games (ms)", title="Only blocking breaks the frame budget")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out / "fig_tick.png", dpi=150)
    plt.close(fig)

    sel = exp[(exp.arch.isin(["rules", "blocking"])) | (exp.budget_ms == 250)]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    pairs = sel[["arch", "budget_ms"]].drop_duplicates().itertuples(index=False)
    labels = [label(a, b) for a, b in sorted(pairs, key=lambda p: ORDER.index(p[0]))]
    width = 0.8 / len(labels)
    for i, lab in enumerate(labels):
        part = sel[sel.label == lab].set_index("skill").reindex(SKILLS)
        arch = lab.split(" ")[0]
        xs = [k + (i - (len(labels) - 1) / 2) * width for k in range(len(SKILLS))]
        ax.bar(xs, part.death_rate, width=width * 0.9, color=STYLE[arch][0], label=lab)
    ax.set_xticks(range(len(SKILLS)))
    ax.set_xticklabels([f"{s} bot" for s in SKILLS])
    ax.yaxis.set_major_formatter(pct)
    ax.set(ylabel="games ending in death", title="Death rate per skill (async, cache, prefetch at 250 ms)")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "fig_experience.png", dpi=150)
    plt.close(fig)

    print((out / "main_table.md").read_text())


if __name__ == "__main__":
    main()
