"""Step 6: record real Jev behaviour once, replay it as often as needed.

Two things vary from run to run when you talk to the real Jev: how long each
request takes (the network) and, possibly, what it answers. A recording pins down both:

  latencies.csv  one row per request, in the order they were sent (same columns
                 as the Step 0 CSV, so a Step 0 run is also a valid recording)
  answers.json   state text -> Jev's decision. The game's state texts are
                 deterministic (rounded numbers, seeded game), so the same game
                 produces the same texts and finds its answers again.

Replaying = a SimulatedJev whose answers come from answers.json and whose
latencies come from latencies.csv, on the simulated clock. Nothing random is
left, so two replays give identical results, and a replay of a recorded run
reproduces that run exactly.
"""

from __future__ import annotations

import csv
import json
import math
import threading
import zlib
from pathlib import Path

from .decision import Decision, DecisionState, state_to_text
from .deciders import Answer


class RecordedLatency:
    """Latencies in recorded order. `offset` starts somewhere else in the
    recording (e.g. per seed), wrapping around at the end."""

    def __init__(self, csv_path: str | Path, condition: str | None = None, offset: int = 0):
        with open(csv_path, newline="") as f:
            rows = [r for r in csv.DictReader(f)
                    if condition is None or r.get("condition", condition) == condition]
        if not rows:
            raise ValueError(f"no latencies in {csv_path}")
        self.values = [float(r["latency_ms"]) if r.get("ok", "1") in ("1", "True") else math.inf
                       for r in rows]
        self.i = offset % len(self.values)

    def sample_ms(self) -> float:
        v = self.values[self.i]
        self.i = (self.i + 1) % len(self.values)
        return v

    @staticmethod
    def offset_for(seed: int, *parts) -> int:
        """A fixed, well-spread starting point per seed and configuration."""
        return zlib.crc32(repr((seed, *parts)).encode())


class AnswerStore:
    """state text -> decision, saved as JSON. Safe to use from several threads."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()
        if self.path and self.path.exists():
            self._data = json.loads(self.path.read_text())

    def get(self, text: str) -> tuple[Decision, int] | None:
        e = self._data.get(text)
        if e is None:
            return None
        return Decision(e["count"], e["mult"], source="jev"), e.get("tokens", 0)

    def put(self, text: str, d: Decision, tokens: int) -> None:
        with self._lock:
            self._data[text] = {"count": d.count, "mult": d.mult, "tokens": tokens}

    def __len__(self) -> int:
        return len(self._data)

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                self.path.write_text(json.dumps(self._data, indent=0, sort_keys=True))


class MissingAnswer(KeyError):
    pass


class StoreAnswers:
    """An answer source backed by an AnswerStore.

    On a miss it asks `fallback` (another answer source) and stores the result,
    or raises MissingAnswer if there is no fallback (strict replay).
    """

    def __init__(self, store: AnswerStore, fallback=None):
        self.store = store
        self.fallback = fallback
        self.hits = self.misses = 0

    def answer(self, state: DecisionState, text: str) -> tuple[Decision, int]:
        got = self.store.get(text)
        if got is not None:
            self.hits += 1
            return got
        self.misses += 1
        if self.fallback is None:
            raise MissingAnswer(text)
        d, tokens = self.fallback.answer(state, text)
        self.store.put(text, d, tokens)
        return d, tokens


class RecordingDecider:
    """Wraps the live Jev: every request is answered live, and its latency and
    answer are written to the recording.

    `real_time` is False on purpose: in record mode the game runs on the
    simulated clock, and the measured latency is charged as virtual time. So the
    recording run is itself a normal experiment, and replaying it gives the same result.
    """

    real_time = False
    FIELDS = ["i", "latency_ms", "ok", "input_tokens", "error", "count", "mult", "state_text"]

    def __init__(self, live_decider, latencies_csv: str | Path, store: AnswerStore):
        self.live = live_decider
        self.store = store
        self.path = Path(latencies_csv)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        self._f = self.path.open("a", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=self.FIELDS)
        if new:
            self._w.writeheader()
        self._n = 0

    def decide(self, state: DecisionState) -> Answer:
        ans = self.live.decide(state)
        text = state_to_text(state)
        self._n += 1
        self._w.writerow({
            "i": self._n, "latency_ms": f"{ans.latency_ms:.2f}", "ok": int(ans.ok),
            "input_tokens": ans.input_tokens, "error": ans.error,
            "count": ans.decision.count if ans.decision else "",
            "mult": ans.decision.mult if ans.decision else "", "state_text": text,
        })
        self._f.flush()
        if ans.ok and ans.decision is not None:
            self.store.put(text, ans.decision, ans.input_tokens)
        return ans

    def close(self) -> None:
        self._f.close()
        self.store.save()
        if hasattr(self.live, "close"):
            self.live.close()
