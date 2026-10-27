"""Tables and figures for the results chapter.

    python analysis/results.py                                   (from text-game/)
    python analysis/results.py --sweep results/sim/live-20261027_0720

Reads the Step 0 CSVs (results/step0/) and one simulator sweep (games.csv,
spells.csv), and writes results/thesis/:
    tables.md            every table, in markdown
    tables.tex           the same tables, LaTeX booktabs
    fig*.pdf / fig*.png  the figures (PDF for the thesis, PNG for previews)

Needs pandas and matplotlib (pip install pandas matplotlib).
"""

import argparse
import glob
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DEADLINES = [33, 167, 200, 233, 333]
FRAME_MS = 1000 / 30
ARCHS = ["async", "cache", "prefetch"]
SKILLS = ["weak", "average", "strong"]

# Categorical slots 1-3 of the reference palette; references in neutral gray.
# Each series also has its own marker and line style, so the figures read in print.
COLOR = {"async": "#2a78d6", "cache": "#eb6834", "prefetch": "#1baf7a"}
MARKER = {"async": "o", "cache": "s", "prefetch": "^"}
LINE = {"async": "-", "cache": "--", "prefetch": "-."}
INK, INK2, GRID, REF = "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "legend.frameon": False, "lines.linewidth": 2,
    "lines.markersize": 7, "figure.dpi": 150, "savefig.bbox": "tight",
})


def ci95(xs):
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    return 1.96 * sd / math.sqrt(len(xs))


def frames(ms):
    return round(ms / FRAME_MS)


# ------------------------------------------------------------------ data

def load(sweep):
    games = pd.read_csv(os.path.join(sweep, "games.csv"))
    spells = pd.read_csv(os.path.join(sweep, "spells.csv"))
    games["deadline_ms"] = games["deadline_ms"].fillna(0).astype(int)
    spells["deadline_ms"] = spells["deadline_ms"].fillna(0).astype(int)
    step0 = pd.concat([pd.read_csv(f).assign(file=os.path.basename(f))
                       for f in sorted(glob.glob("results/step0/jev_spell_latency*.csv"))], ignore_index=True)
    meta = json.load(open(os.path.join(sweep, "meta.json")))
    rec = os.path.join(meta.get("recording") or "", "answers.json")
    sweep_lat = []
    if os.path.exists(rec):
        sweep_lat = [a["latencyMs"] for v in json.load(open(rec)).values() for a in v if a.get("ok")]
    return games, spells, step0, sweep_lat


def cells(games):
    """One row per architecture x deadline, pooled over skills (as summary.md)."""
    rows = []
    for (arch, dl), g in games.groupby(["arch", "deadline_ms"]):
        n_sp = g["spells"].sum()
        reqs = g["requests"].sum() + g["prefetch_requests"].sum()
        rows.append({
            "arch": arch, "deadline": dl, "games": len(g),
            "share": g["model_share"].mean(), "share_ci": ci95(list(g["model_share"])),
            "wait": g["mean_wait_ms"].mean(), "p95": g["p95_wait_ms"].mean(),
            "req_per_spell": reqs / n_sp if n_sp else float("nan"),
            "acc": g["element_accuracy"].mean(), "acc_ci": ci95(list(g["element_accuracy"])),
            "rules_acc": g["rules_element_accuracy"].mean(),
            "cost_h": g["cost_per_hour_usd"].mean(), "worst_tick": g["worst_tick_ms"].max(),
            "won": g["won"].mean(), "hearts": g["hearts"].mean(), "kills": g["kills"].mean(),
        })
    order = {a: i for i, a in enumerate(["rules", "blocking"] + ARCHS)}
    return pd.DataFrame(rows).sort_values(["arch", "deadline"], key=lambda s: s.map(order) if s.name == "arch" else s)


# ------------------------------------------------------------------ tables

class Tables:
    def __init__(self):
        self.md, self.tex = [], []

    def add(self, title, label, header, rows, note="", align=None):
        self.md += [f"## {title}", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        self.md += ["| " + " | ".join(r) + " |" for r in rows]
        if note:
            self.md += ["", note]
        self.md.append("")
        esc = lambda s: s.replace("%", r"\%").replace("$", r"\$").replace("±", r"$\pm$").replace("≤", r"$\le$").replace("–", "--").replace("_", r"\_")
        align = align or "l" + "r" * (len(header) - 1)
        self.tex += [r"\begin{table}[ht]", r"\centering", r"\small", rf"\caption{{{esc(title)}}}", rf"\label{{tab:{label}}}",
                     rf"\begin{{tabular}}{{{align}}}", r"\toprule", " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
        self.tex += [" & ".join(esc(c) for c in r) + r" \\" for r in rows]
        self.tex += [r"\bottomrule", r"\end{tabular}"]
        if note:
            self.tex.append(rf"\par\smallskip\footnotesize {esc(note)}")
        self.tex += [r"\end{table}", ""]


pct = lambda x: "–" if pd.isna(x) else f"{100 * x:.0f}%"
ms = lambda x: "–" if pd.isna(x) else f"{x:.0f} ms"


def dl_label(d):
    return "–" if not d else f"{d} ms ({frames(d)})"


def step0_tables(t, s0, sweep_lat):
    dls = [33, 100, 167, 200, 233, 333, 500]
    rows = []
    for c in ["warm", "cold", "same", "long", "inject"]:
        r = s0[s0.condition == c]
        if r.empty:
            continue
        lat = r[r.ok == 1].latency_ms
        rows.append([c, str(len(r)), str(int((r.ok != 1).sum())), ms(lat.median()), ms(lat.quantile(0.95)), ms(lat.max())]
                    + [pct((lat <= d).sum() / len(r)) for d in dls])
    if sweep_lat:
        sl = pd.Series(sweep_lat)
        rows.append(["during the sweep", str(len(sl)), "0", ms(sl.median()), ms(sl.quantile(0.95)), ms(sl.max())]
                    + [pct((sl <= d).mean()) for d in dls])
    t.add("Jev latency on the spell request (Step 0, and live during the sweep)", "step0-latency",
          ["condition", "n", "errors", "median", "p95", "max"] + [f"≤ {d}" for d in dls], rows,
          "Failures count as misses. 'during the sweep' = every answer the live sweep received.")

    ok = s0[s0.ok == 1]
    lab = ok[ok.label_element.notna() & ok.condition.isin(["warm", "cold"])]
    rows = [[q, pct((lab[q] == lab[f"label_{q}"]).mean()), pct((lab[f"rules_{q}"] == lab[f"label_{q}"]).mean())]
            for q in ["element", "target", "power"]]
    valid = s0[s0.http_status == 200]
    t.add("Agreement with the corpus labels (Step 0, warm and cold)", "step0-agreement",
          ["question", "Jev", "keyword rules"], rows,
          f"{len(lab)} labelled requests. Format validity: {int(valid.valid.sum())} of {len(valid)} answers parsed ({pct(valid.valid.mean())}).")


def sweep_tables(t, c, games):
    rows = []
    for _, r in c.iterrows():
        rows.append([r.arch, dl_label(r.deadline), f"{pct(r.share)} ± {100 * r.share_ci:.0f}", ms(r.wait), ms(r.p95),
                     f"{r.req_per_spell:.2f}" if r.arch != "rules" else "–", pct(r.acc), pct(r.rules_acc),
                     f"${r.cost_h:.3f}", ms(r.worst_tick)])
    t.add("Architectures by deadline (live Jev, all skills pooled)", "sweep-main",
          ["architecture", "deadline (frames)", "decided by model", "mean wait", "p95 wait", "requests / spell",
           "element right", "rules on same spells", "cost / hour", "worst tick"], rows,
          "Mean over games with a 95% CI over games. Requests include prefetches. The tick budget is 33 ms.",
          align="llrrrrrrrr")

    rows = []
    for arch in ARCHS:
        for d in DEADLINES:
            g = games[(games.arch == arch) & (games.deadline_ms == d)]
            rows.append([arch, dl_label(d)] + [pct(g[g.skill == s].model_share.mean()) for s in SKILLS])
    t.add("Share decided by the model, by player skill", "sweep-skill", ["architecture", "deadline (frames)"] + SKILLS, rows,
          "Stronger bot players reuse spells more often (30% against 10%), so cache and prefetch find more answers already there.", align="llrrr")

    rows = []
    for _, r in c[c.deadline.isin([0, 200])].iterrows():
        rows.append([r.arch, dl_label(r.deadline), pct(r.won), f"{r.hearts:.1f}", f"{r.kills:.1f}"])
    t.add("Game outcome (deadline 200 ms)", "sweep-outcome", ["architecture", "deadline (frames)", "games won", "hearts left", "gloomlings beaten"], rows,
          "Outcome depends on the bot as much as on the decisions; reported for completeness.", align="llrrr")


# ------------------------------------------------------------------ figures

def save(fig, name, out):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out, f"{name}.{ext}"))
    plt.close(fig)


def deadline_axis(ax):
    ax.set_xticks(DEADLINES)
    ax.set_xticklabels([f"{d}\n({frames(d)} fr)" for d in DEADLINES])
    ax.set_xlabel("deadline, ms (frames at 30 fps)")


def fig_latency(s0, sweep_lat, out):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    series = [("Step 0, warm", s0[(s0.condition == "warm") & (s0.ok == 1)].latency_ms, "#2a78d6", "-"),
              ("Step 0, cold", s0[(s0.condition == "cold") & (s0.ok == 1)].latency_ms, "#eb6834", "--")]
    if sweep_lat:
        series.append(("during the sweep", pd.Series(sweep_lat), "#1baf7a", "-."))
    for name, lat, col, ls in series:
        x = lat.sort_values().to_numpy()
        y = [(i + 1) / len(x) for i in range(len(x))]
        ax.plot(x, y, color=col, ls=ls, label=f"{name} (median {x[len(x) // 2]:.0f} ms)")
    for d in DEADLINES:
        ax.axvline(d, color=REF, lw=1, ls=":")
        ax.text(d, 1.02, f"{d}", ha="center", va="bottom", color=INK2, fontsize=8)
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_xlabel("latency, ms (dotted: the deadlines tested)")
    ax.set_ylabel("answers back by then")
    ax.legend(loc="lower right")
    save(fig, "fig1_latency_cdf", out)


def fig_lines(c, out, name, col, ylabel, ci=None, refs=(), percent=True, ylim=None):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for arch in ARCHS:
        r = c[c.arch == arch].sort_values("deadline")
        y = r[col]
        ax.errorbar(r.deadline, y, yerr=r[ci] if ci else None, color=COLOR[arch], marker=MARKER[arch], ls=LINE[arch],
                    capsize=3, label=arch, markeredgecolor="white", markeredgewidth=1)
    for label, value in refs:
        ax.axhline(value, color=REF, lw=1.2, ls=":")
        ax.text(DEADLINES[-1] + 8, value, label, va="center", color=INK2, fontsize=8)
    deadline_axis(ax)
    ax.set_xlim(20, 380)
    if ylim:
        ax.set_ylim(*ylim)
    if percent:
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_ylabel(ylabel)
    ax.legend(loc="best")
    save(fig, name, out)


def fig_cost(c, out):
    r = c[c.deadline.isin([0, 200])].copy()
    order = ["rules", "blocking"] + ARCHS
    r["o"] = r.arch.map(order.index)
    r = r.sort_values("o")
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    colors = [COLOR.get(a, REF) for a in r.arch]
    bars = ax.bar(r.arch, r.req_per_spell, color=colors, width=0.6, edgecolor="white", linewidth=2)
    for b, (_, row) in zip(bars, r.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, f"{row.req_per_spell:.2f}\n${row.cost_h:.3f}/h",
                ha="center", va="bottom", color=INK, fontsize=8)
    ax.set_ylabel("requests per spell cast")
    ax.set_ylim(0, max(r.req_per_spell) * 1.35)
    ax.grid(axis="x", visible=False)
    ax.set_title("Deadline 200 ms; labels give requests per spell and cost per hour of play", fontsize=9, color=INK2)
    save(fig, "fig5_requests_cost", out)


def fig_blocking(spells, out):
    b = spells[(spells.arch == "blocking") & spells.latency_ms.notna()].latency_ms
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.hist(b, bins=range(100, 520, 10), color=REF, edgecolor="white", linewidth=1)
    ax.axvline(FRAME_MS, color="#e34948", lw=1.5)
    ax.text(FRAME_MS + 5, ax.get_ylim()[1] * 0.9, "33 ms frame budget", color=INK, fontsize=8)
    ax.set_xlim(0, 520)
    ax.set_xlabel("frozen tick, ms (blocking: the game waits for Jev inside the tick)")
    ax.set_ylabel("spells")
    ax.text(0.98, 0.9, f"{len(b)} spells, median {b.median():.0f} ms,\nevery one over budget ({(b > FRAME_MS).mean():.0%})",
            transform=ax.transAxes, ha="right", va="top", color=INK2, fontsize=8)
    save(fig, "fig6_blocking_freeze", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default=max(glob.glob("results/sim/live-*"), default=None))
    ap.add_argument("--out", default="results/thesis")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    games, spells, s0, sweep_lat = load(a.sweep)
    c = cells(games)

    t = Tables()
    step0_tables(t, s0, sweep_lat)
    sweep_tables(t, c, games)
    head = f"# Results tables\n\nFrom `{a.sweep}` ({len(games)} games, {len(spells)} spells) and {s0.file.nunique()} Step 0 runs ({len(s0)} requests). Made by analysis/results.py.\n"
    open(os.path.join(a.out, "tables.md"), "w").write(head + "\n" + "\n".join(t.md))
    open(os.path.join(a.out, "tables.tex"), "w").write("% needs \\usepackage{booktabs}\n" + "\n".join(t.tex))

    blocking = c[c.arch == "blocking"].iloc[0]
    rules = c[c.arch == "rules"].iloc[0]
    fig_latency(s0, sweep_lat, a.out)
    fig_lines(c, a.out, "fig2_model_share", "share", "spells decided by the model", ci="share_ci",
              refs=[("blocking", 1.0), ("rules", 0.0)], ylim=(-0.03, 1.05))
    fig_lines(c, a.out, "fig3_wait", "wait", "mean wait from Enter to cast, ms", percent=False,
              refs=[(f"blocking ({blocking.wait:.0f} ms, frozen)", blocking.wait)], ylim=(0, 240))
    fig_lines(c, a.out, "fig4_accuracy", "acc", "element matches the label", ci="acc_ci",
              refs=[(f"blocking {blocking.acc:.0%}", blocking.acc), (f"rules {rules.acc:.0%}", rules.acc)], ylim=(0.5, 1.0))
    fig_cost(c, a.out)
    fig_blocking(spells, a.out)
    print(f"Written {a.out}/tables.md, tables.tex and 6 figures.")


if __name__ == "__main__":
    main()
