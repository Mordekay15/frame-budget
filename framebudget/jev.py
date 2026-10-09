"""A small client for Jev (TypeSafe) through OpenRouter's Decisions API.

Jev is not a chat model. A request carries
  - `state`: a description of the situation (we send a short text),
  - `questions`: named, typed questions. We use two "choice" questions,
and the response carries one typed answer per question, with probabilities.

    POST https://openrouter.ai/api/alpha/decisions
    Authorization: Bearer <OPENROUTER_API_KEY>
    {"model": "typesafe/jev-1.13", "state": "...", "questions": {...}}

The client keeps one HTTPS connection open between requests ("keep-alive").
Opening a new connection costs a TCP and TLS handshake, which can add 50-150 ms,
so a game would always reuse the connection. `fresh_connection=True` measures
the other case.

Only the standard library is used, so this works without installing anything.
"""

from __future__ import annotations

import http.client
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .decision import DAMAGE_MULTS, ENEMY_COUNTS, Decision

HOST = "openrouter.ai"
PATH = "/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"  # pinned, so results don't move if "latest" changes
PRICE_PER_M_INPUT_TOKENS = 0.042  # USD, output tokens are free (Oct 2026)

INSTRUCTIONS_COUNT = (
    "You tune the difficulty of an action game. The goal is to keep the player "
    "challenged but not overwhelmed: they should lose health, but not die. "
    "How many enemies should the next wave contain?"
)
INSTRUCTIONS_MULT = (
    "You tune the difficulty of an action game. The goal is to keep the player "
    "challenged but not overwhelmed: they should lose health, but not die. "
    "How hard should the enemies of the next wave hit?"
)

# Choice keys must be plain names; we map them back to numbers below.
COUNT_KEYS = {f"enemies_{n}": n for n in ENEMY_COUNTS}
MULT_KEYS = {"soft": 0.75, "normal": 1.0, "hard": 1.25, "brutal": 1.5}
assert tuple(MULT_KEYS.values()) == DAMAGE_MULTS

QUESTIONS = {
    "enemy_count": {
        "type": "choice",
        "instructions": INSTRUCTIONS_COUNT,
        "criteria": {
            "enemies_3": "3 enemies: a very light wave, for a player close to dying",
            "enemies_5": "5 enemies: a light wave",
            "enemies_8": "8 enemies: a heavy wave",
            "enemies_12": "12 enemies: a very heavy wave, for a player who is never hurt",
        },
    },
    "damage_mult": {
        "type": "choice",
        "instructions": INSTRUCTIONS_MULT,
        "criteria": {
            "soft": "Enemies deal 0.75x damage: easier",
            "normal": "Enemies deal 1x damage: standard",
            "hard": "Enemies deal 1.25x damage: harder",
            "brutal": "Enemies deal 1.5x damage: much harder",
        },
    },
}


def load_api_key(env_file: str | os.PathLike = ".env") -> str:
    """Read OPENROUTER_API_KEY from the environment, or from a local .env file."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    p = Path(env_file)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "No API key. Put OPENROUTER_API_KEY=sk-or-... in a .env file in the repo root "
        "(see docs/JEV_GUIDE.md), or export it in your shell."
    )


@dataclass
class JevResult:
    """One request: timing, cost and the parsed decision (if it succeeded)."""

    latency_ms: float
    ok: bool
    http_status: int = 0
    error: str = ""
    decision: Decision | None = None
    count_confidence: float = 0.0
    mult_confidence: float = 0.0
    count_probs: dict = field(default_factory=dict)
    mult_probs: dict = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    served_model: str = ""
    provider: str = ""


def parse_answers(body: dict) -> tuple[Decision, dict]:
    """Turn Jev's JSON answers into a Decision plus extra fields."""
    answers = body["answers"]
    c, m = answers["enemy_count"], answers["damage_mult"]
    decision = Decision(COUNT_KEYS[c["choice"]], MULT_KEYS[m["choice"]], source="jev")
    extra = dict(
        count_confidence=float(c.get("confidence", 0.0)),
        mult_confidence=float(m.get("confidence", 0.0)),
        count_probs=c.get("probabilities", {}),
        mult_probs=m.get("probabilities", {}),
    )
    return decision, extra


class JevClient:
    def __init__(self, api_key: str, model: str = MODEL, timeout_s: float = 10.0):
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self._conn: http.client.HTTPSConnection | None = None

    def _connection(self, fresh: bool) -> http.client.HTTPSConnection:
        if fresh or self._conn is None:
            self.close()
            self._conn = http.client.HTTPSConnection(HOST, timeout=self.timeout_s)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def decide(self, state_text: str, fresh_connection: bool = False) -> JevResult:
        """Send one request and time it. Never raises: failures come back as ok=False."""
        payload = json.dumps(
            {"model": self.model, "state": state_text, "questions": QUESTIONS}
        ).encode()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        t0 = time.perf_counter()
        try:
            conn = self._connection(fresh_connection)
            conn.request("POST", PATH, body=payload, headers=headers)
            resp = conn.getresponse()
            raw = resp.read()
            latency = (time.perf_counter() - t0) * 1000
        except Exception as exc:  # network error, timeout, ...
            latency = (time.perf_counter() - t0) * 1000
            self.close()  # the connection may be broken; open a new one next time
            return JevResult(latency, ok=False, error=f"{type(exc).__name__}: {exc}")

        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            return JevResult(latency, False, resp.status, error=raw[:200].decode(errors="replace"))
        if resp.status != 200 or "error" in body:
            return JevResult(latency, False, resp.status, error=json.dumps(body.get("error", body))[:300])

        try:
            decision, extra = parse_answers(body)
        except (KeyError, TypeError) as exc:
            return JevResult(latency, False, resp.status, error=f"unexpected answer shape: {exc!r}")
        usage = body.get("usage", {})
        return JevResult(
            latency,
            True,
            resp.status,
            decision=decision,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            cost=float(usage.get("cost", 0.0) or 0.0),
            served_model=body.get("model", ""),
            provider=body.get("provider", ""),
            **extra,
        )

    def raw_request(self, state_text: str) -> dict:
        """One request, returning Jev's full JSON. Used by scripts/jev_hello.py."""
        conn = self._connection(fresh=True)
        conn.request(
            "POST",
            PATH,
            body=json.dumps({"model": self.model, "state": state_text, "questions": QUESTIONS}),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        return {"http_status": resp.status, "body": json.loads(resp.read() or b"{}")}
