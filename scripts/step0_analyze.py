"""Step 0 analysis: latency distribution, budget shares, cost and consistency.

    python -m scripts.step0_analyze results/step0/jev_latency.csv

Writes summary.md, latency_hist.png and latency_ecdf.png next to the CSV.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from framebudget.jev import PRICE_PER_M_INPUT_TOKENS

BUDGETS_MS = (33, 100, 250, 500)
COLORS = {"warm": "#2a6fdb", "cold": "#e07b39", "same": "#4c9f70"}


def latency_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cond, g in df.groupby("condition", sort=False):
        ok = g[g.ok == 1].latency_ms
        row = {
            "condition": cond, "n": len(g), "errors": int((g.ok == 0).sum()),
            "median_ms": ok.median(), "p95_ms": ok.quantile(0.95),
            "p99_ms": ok.quantile(0.99), "max_ms": ok.max(),
        }
        for b in BUDGETS_MS:
            # A failed request never meets a deadline, so it counts against every budget.
            row[f"under_{b}ms"] = float((g.ok.eq(1) & g.latency_ms.le(b)).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def consistency(df: pd.DataFrame) -> str:
    g = df[(df.condition == "same") & (df.ok == 1)]
    if g.empty:
        return "No `same` requests.\n"
    lines = [f"{len(g)} requests with one identical state.\n"]
    for col in ("count", "mult"):
        share = g[col].value_counts(normalize=True)
        lines.append(f"- `{col}` answers: " + ", ".join(f"{k}: {v:.0%}" for k, v in share.items()))
        probs = pd.DataFrame([json.loads(p) for p in g[f"{col}_probs"]])
        if not probs.empty:
            lines.append(f"  - largest std of a probability across repeats: {probs.std().max():.4f}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    path = Path(args.csv)
    df = pd.read_csv(path)
    outdir = path.parent

    table = latency_table(df)
    ok = df[df.ok == 1]
    tokens = ok.input_tokens.mean()
    # A decision every ~5 s of play is roughly one per wave (see Step 2).
    per_hour = 3600 / 5
    cost_hour = per_hour * tokens * PRICE_PER_M_INPUT_TOKENS / 1e6
    reported = ok.cost.sum()

    fmt = table.copy()
    for c in fmt.columns:
        if c.startswith("under_"):
            fmt[c] = fmt[c].map(lambda v: f"{v:.0%}")
        elif c.endswith("_ms"):
            fmt[c] = fmt[c].map(lambda v: f"{v:.0f}")
    md = [
        f"# Step 0 results: `{path.name}`\n",
        f"Served by: {', '.join(sorted(set(map(str, ok.served_model))))}  ",
        f"First request: {df.started_at.min()}  ",
        f"Last request: {df.started_at.max()}\n",
        "## Latency\n",
        fmt.to_markdown(index=False) if hasattr(fmt, "to_markdown") else fmt.to_string(index=False),
        "\n`under_Xms` is the share of requests that succeeded within X ms, i.e. how often a",
        "decision with that deadline would have arrived in time.\n",
        "## Cost\n",
        f"Mean input tokens per request: {tokens:.0f}. Cost reported by the API for this run: ${reported:.5f}.",
        f"At one decision every 5 s, an hour of play is {per_hour:.0f} requests, about ${cost_hour:.4f}.\n",
        "## Consistency (same state repeated)\n",
        consistency(df),
    ]
    (outdir / "summary.md").write_text("\n".join(md))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    hi = ok.latency_ms.quantile(0.995)
    bins = np.linspace(0, hi, 60)
    for cond, g in ok.groupby("condition", sort=False):
        ax.hist(g.latency_ms.clip(upper=hi), bins=bins, alpha=0.55, label=cond, color=COLORS.get(cond))
    for b in BUDGETS_MS:
        ax.axvline(b, color="#555", ls="--", lw=1)
        ax.text(b, ax.get_ylim()[1] * 0.95, f" {b} ms", fontsize=8, color="#555")
    ax.set(xlabel="latency (ms)", ylabel="requests", title="Jev latency per request")
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / "latency_hist.png", dpi=150)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for cond, g in ok.groupby("condition", sort=False):
        x = np.sort(g.latency_ms)
        ax.step(x, np.arange(1, len(x) + 1) / len(x), where="post", label=cond, color=COLORS.get(cond))
    for b in BUDGETS_MS:
        ax.axvline(b, color="#555", ls="--", lw=1)
    ax.set(xlabel="latency (ms)", ylabel="share of requests at or below", title="Jev latency, cumulative (ECDF)")
    ax.set_xlim(0, hi)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / "latency_ecdf.png", dpi=150)

    print((outdir / "summary.md").read_text())


if __name__ == "__main__":
    main()
