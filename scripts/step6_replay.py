"""Step 6: record a run with the real Jev once, then replay it identically.

Record (needs your key; one request per wave, ~3 requests per second):

    python -m scripts.step6_replay --record --name jev-2026-10 --games 5

Replay (offline, as often as you like):

    python -m scripts.step6_replay --name jev-2026-10 --games 5

Without --name, a synthetic recording is made with the simulated Jev, so the
whole mechanism can be tried without a key.

The experiment is the Step 5 architecture (async + rules fallback) with a 250 ms
deadline, every skill, `--games` games each, on the simulated clock. A replay runs
it twice and checks that both runs are identical, and identical to the recorded run.
Recordings live in data/recordings/<name>/; results in results/step6/.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from framebudget.arch import AsyncFallback
from framebudget.channel import SimChannel
from framebudget.deciders import FakeAnswers, SimulatedJev
from framebudget.game import SKILLS
from framebudget.latency import LognormalLatency
from framebudget.replay import AnswerStore, RecordedLatency, RecordingDecider, StoreAnswers
from framebudget.sim import run_episode

BUDGET_MS = 250.0


def play(decider, games: int) -> pd.DataFrame:
    rows = []
    for skill in SKILLS:
        for seed in range(games):
            arch = AsyncFallback(SimChannel(decider), BUDGET_MS)
            rows.append(run_episode(arch, skill, seed).row())
    return pd.DataFrame(rows)


def roundtrip(df: pd.DataFrame) -> pd.DataFrame:
    """Write and read back as CSV, so frames compare exactly like the saved files."""
    import io

    return pd.read_csv(io.StringIO(df.to_csv(index=False)))


def digest(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()[:16]


def record(rec: Path, games: int, live: bool) -> pd.DataFrame:
    if (rec / "latencies.csv").exists():
        raise SystemExit(f"{rec} already exists; pick another --name or delete it")
    if live:
        from framebudget.deciders import LiveJevDecider
        from framebudget.jev import JevClient, load_api_key

        inner = LiveJevDecider(JevClient(load_api_key()))
    else:
        inner = SimulatedJev(FakeAnswers(seed=0), LognormalLatency(seed=0))
    store = AnswerStore(rec / "answers.json")
    recorder = RecordingDecider(inner, rec / "latencies.csv", store)
    print(f"Recording into {rec} ({'LIVE Jev' if live else 'simulated Jev'}) ...")
    df = play(recorder, games)
    recorder.close()
    df.to_csv(rec / "recorded_run.csv", index=False)
    print(f"{len(store)} answers and {recorder._n} latencies recorded.")
    return df


def replay(rec: Path, games: int) -> pd.DataFrame:
    store = AnswerStore(rec / "answers.json")
    decider = SimulatedJev(StoreAnswers(store), RecordedLatency(rec / "latencies.csv"))
    return play(decider, games)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default=None, help="recording name (default: synthetic demo)")
    ap.add_argument("--record", action="store_true", help="record with the live Jev")
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--out", default="results/step6")
    args = ap.parse_args()

    name = args.name or "synthetic-demo"
    rec = Path("data/recordings") / name
    if args.record:
        record(rec, args.games, live=True)
        print("Now replay it: python -m scripts.step6_replay --name", name, "--games", args.games)
        return
    if not (rec / "latencies.csv").exists():
        if args.name:
            raise SystemExit(f"No recording {rec}. Record it first with --record.")
        record(rec, args.games, live=False)

    a, b = roundtrip(replay(rec, args.games)), roundtrip(replay(rec, args.games))
    same = a.equals(b)
    lines = [
        f"# Step 6: replay of `{name}`\n",
        f"Experiment: async + rules fallback, deadline {BUDGET_MS:.0f} ms, {args.games} games per skill.\n",
        f"- replay 1 digest: `{digest(a)}`",
        f"- replay 2 digest: `{digest(b)}`",
        f"- **replays identical: {same}**",
    ]
    recorded = rec / "recorded_run.csv"
    if recorded.exists():
        r = pd.read_csv(recorded)
        lines.append(f"- recorded run digest: `{digest(r)}`, replay equals recorded run: "
                     f"**{a.equals(r)}**")
    lines += ["", a.groupby("skill", sort=False)[["deadline_met", "fallback_rate", "died"]].mean()
              .round(3).to_markdown()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"summary_{name}.md").write_text("\n".join(lines) + "\n")
    print((out / f"summary_{name}.md").read_text())
    if not same:
        raise SystemExit("Replays differ: something is still non-deterministic.")


if __name__ == "__main__":
    main()
