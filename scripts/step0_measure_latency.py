"""Step 0: measure Jev's latency in isolation.

Sends a few hundred requests with random but realistic game states and writes
one CSV row per request. Three conditions:

  warm   requests reuse one open connection (how the game will call Jev)
  cold   every request opens a new connection (cost of the handshake)
  same   one fixed state, many times (does Jev always answer the same?)

Run on your own machine (needs OPENROUTER_API_KEY, see docs/JEV_GUIDE.md):

    python -m scripts.step0_measure_latency
    python -m scripts.step0_measure_latency --fake     # offline dry run, no key

Then analyse with `python -m scripts.step0_analyze results/step0/jev_latency.csv`.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import time
from pathlib import Path

from framebudget.decision import DAMAGE_MULTS, ENEMY_COUNTS, DecisionState, state_to_text
from framebudget.fakejev import FakeJevClient
from framebudget.jev import JevClient, load_api_key

FIELDS = [
    "condition", "i", "started_at", "latency_ms", "ok", "http_status", "error",
    "input_tokens", "output_tokens", "cost", "served_model", "provider",
    "count", "mult", "count_confidence", "mult_confidence", "count_probs", "mult_probs",
    "state_text",
]


def random_state(rng: random.Random) -> DecisionState:
    """A state that could plausibly come out of the game (see Step 2)."""
    count = rng.choice(ENEMY_COUNTS)
    mult = rng.choice(DAMAGE_MULTS)
    kill_rate = rng.uniform(0.5, 4.0)
    clear = count / kill_rate * rng.uniform(0.8, 1.2)
    dmg = min(100.0, 2.0 * mult * count * (count + 1) / 2 / kill_rate * rng.uniform(0.7, 1.3))
    return DecisionState(
        health=rng.uniform(5, 100), max_health=100, wave=rng.randint(1, 30),
        last_count=count, last_mult=mult, last_wave_damage=dmg, last_clear_time=clear,
        dps_recent=dmg / max(clear, 0.1), kill_rate=kill_rate,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--warm", type=int, default=300, help="requests on one reused connection")
    ap.add_argument("--cold", type=int, default=100, help="requests each on a new connection")
    ap.add_argument("--same", type=int, default=30, help="requests repeating one fixed state")
    ap.add_argument("--gap-ms", type=float, default=200, help="pause between requests")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/step0/jev_latency.csv")
    ap.add_argument("--fake", action="store_true", help="offline dry run with a fake Jev")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    client = FakeJevClient(seed=args.seed) if args.fake else JevClient(load_api_key())
    fixed_state = state_to_text(random_state(random.Random(12345)))

    plan = (
        [("warm", lambda: state_to_text(random_state(rng)), False)] * args.warm
        + [("cold", lambda: state_to_text(random_state(rng)), True)] * args.cold
        + [("same", lambda: fixed_state, False)] * args.same
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # One unmeasured request first, so the "warm" condition starts with an open connection.
    client.decide(fixed_state)

    counters: dict[str, int] = {}
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for n, (cond, make_state, fresh) in enumerate(plan, 1):
            text = make_state()
            started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
            r = client.decide(text, fresh_connection=fresh)
            i = counters[cond] = counters.get(cond, 0) + 1
            w.writerow({
                "condition": cond, "i": i, "started_at": started,
                "latency_ms": f"{r.latency_ms:.2f}", "ok": int(r.ok),
                "http_status": r.http_status, "error": r.error,
                "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                "cost": r.cost, "served_model": r.served_model, "provider": r.provider,
                "count": r.decision.count if r.decision else "",
                "mult": r.decision.mult if r.decision else "",
                "count_confidence": r.count_confidence, "mult_confidence": r.mult_confidence,
                "count_probs": json.dumps(r.count_probs), "mult_probs": json.dumps(r.mult_probs),
                "state_text": text,
            })
            f.flush()  # keep what we have if the run is interrupted
            status = "ok" if r.ok else f"FAILED {r.http_status} {r.error[:60]}"
            print(f"[{n:4d}/{len(plan)}] {cond:4s} {r.latency_ms:7.1f} ms  {status}")
            if not args.fake:
                time.sleep(args.gap_ms / 1000)
    client.close()
    print(f"\nWrote {len(plan)} rows to {out}")


if __name__ == "__main__":
    main()
