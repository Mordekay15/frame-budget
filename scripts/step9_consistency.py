"""Step 9b: consistency. Same state, many times: how much do the decisions differ?

    python -m scripts.step9_consistency                       # simulated Jev
    python -m scripts.step9_consistency --live                # real Jev: 12 states x 30 = 360 requests
    python -m scripts.step9_consistency --latency results/step0/jev_latency.csv

Two levels:
  model level         the raw answers of the decider for an identical input.
  architecture level  what each architecture would actually *apply* for that
                      input, given that answers arrive late at random:
                        rules     always the rules' decision
                        blocking  always the model's answer
                        async     the model's answer if it arrived in time, else the rules'
                        cache     like async the first time, then whatever got cached
                        prefetch  like cache, but the first answer was fetched in advance

Metric per (architecture, deadline, state): agreement = share of repeats that
equal the most common decision (1.0 = perfectly consistent), and the number of
distinct decisions. Writes results/step9/consistency.csv and consistency.md.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

from framebudget.decision import DecisionState, state_to_text
from framebudget.deciders import FakeAnswers
from framebudget.experiment import cell_seed
from framebudget.latency import latency_model
from framebudget.rules import HunickePolicy


def probe_states() -> list[DecisionState]:
    """12 situations covering the range: hurt / mid / healthy x slow / fast players x calm / rough last wave."""
    out = []
    for health in (25, 60, 95):
        for rate in (1.2, 3.5):
            for dmg in (8, 35):
                count = 5
                clear = count / rate
                out.append(DecisionState(health, 100, 6, count, 1.0, dmg, clear, dmg / clear, rate))
    return out


def agreement(decisions: list) -> tuple[float, int]:
    c = Counter(decisions)
    return c.most_common(1)[0][1] / len(decisions), len(c)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeats", type=int, default=30)
    ap.add_argument("--budgets", default="33,100,250,500")
    ap.add_argument("--latency", default="synthetic")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default="results/step9")
    args = ap.parse_args()
    budgets = [float(b) for b in args.budgets.split(",")]

    if args.live:
        from framebudget.jev import load_api_key
        from framebudget.replay import LiveAnswers

        source = LiveAnswers(load_api_key())
    else:
        source = FakeAnswers(seed=1)

    rows = []
    for k, st in enumerate(probe_states()):
        text = state_to_text(st)
        # The raw answers, asked once and reused for every architecture.
        answers = [source.answer(st, text)[0].key() for _ in range(args.repeats)]
        rules = HunickePolicy().decide(st).key()
        a, n = agreement(answers)
        rows.append({"arch": "model", "budget_ms": None, "state": k, "agreement": a, "distinct": n})
        rows.append({"arch": "rules", "budget_ms": None, "state": k, "agreement": 1.0, "distinct": 1})
        rows.append({"arch": "blocking", "budget_ms": None, "state": k, "agreement": a, "distinct": n})
        for b in budgets:
            lat = latency_model(args.latency, cell_seed("consistency", k, b))
            arrived = [lat.sample_ms() <= b for _ in range(args.repeats)]
            async_d = [ans if ok else rules for ans, ok in zip(answers, arrived)]
            # Cache: a decision is fixed once the first answer has come back (in time or not).
            cache_d, cached = [], None
            for ans, ok in zip(answers, arrived):
                cache_d.append(cached if cached else (ans if ok else rules))
                cached = cached or ans
            prefetch_d = [answers[0]] * args.repeats  # fetched before it was needed
            for name, ds in (("async", async_d), ("cache", cache_d), ("prefetch", prefetch_d)):
                a2, n2 = agreement(ds)
                rows.append({"arch": name, "budget_ms": b, "state": k, "agreement": a2, "distinct": n2})

    df = pd.DataFrame(rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "consistency.csv", index=False)
    s = df.groupby(["arch", "budget_ms"], dropna=False).agg(
        agreement=("agreement", "mean"), worst_state=("agreement", "min"), distinct=("distinct", "mean"),
    ).round(3)
    src = "LIVE Jev" if args.live else "simulated Jev (FakeAnswers, noise 0.3)"
    (out / "consistency.md").write_text(
        f"# Consistency ({src}, {args.repeats} repeats x {len(probe_states())} states)\n\n"
        + s.to_markdown() + "\n\nagreement: share of repeats equal to the most common decision, mean over states.\n"
    )
    print((out / "consistency.md").read_text())


if __name__ == "__main__":
    main()
