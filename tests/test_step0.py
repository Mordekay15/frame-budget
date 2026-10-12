import json

import random

from framebudget.decision import DecisionState, state_to_text
from framebudget.fakejev import FakeJevClient
from framebudget.jev import COUNT_KEYS, MULT_KEYS, parse_answers
from scripts.step0_measure_latency import random_state


def test_state_text_is_deterministic():
    a = state_to_text(random_state(random.Random(1)))
    b = state_to_text(random_state(random.Random(1)))
    assert a == b and "Player health" in a


def test_parse_answers_maps_choice_keys_to_numbers():
    body = {"answers": {
        "enemy_count": {"type": "choice", "choice": "enemies_8", "confidence": 0.6,
                        "probabilities": {k: 0.25 for k in COUNT_KEYS}},
        "damage_mult": {"type": "choice", "choice": "hard", "confidence": 0.5,
                        "probabilities": {k: 0.25 for k in MULT_KEYS}},
    }}
    d, extra = parse_answers(body)
    assert (d.count, d.mult, d.source) == (8, 1.25, "jev")
    assert extra["count_confidence"] == 0.6


def test_fake_client_answers_inside_decision_space():
    c = FakeJevClient(seed=3)
    s = DecisionState(20, 100, 3, 8, 1.5, 60, 9.0, 6.0, 0.9)
    r = c.decide(state_to_text(s))
    assert r.ok and r.decision.count in COUNT_KEYS.values() and r.latency_ms > 0


class FakeConnection:
    """Stands in for http.client.HTTPSConnection and records what was sent."""

    sent = []

    def __init__(self, host, timeout=None):
        self.host = host

    def request(self, method, path, body=None, headers=None):
        FakeConnection.sent.append((self.host, path, json.loads(body), headers))

    def getresponse(self):
        class R:
            status = 200

            def read(self_inner):
                return json.dumps({"model": "jev-1.13.0", "answers": {
                    "enemy_count": {"type": "choice", "choice": "enemies_5", "confidence": 0.8,
                                    "probabilities": {}},
                    "damage_mult": {"type": "choice", "choice": "normal", "confidence": 0.7,
                                    "probabilities": {}}},
                    "usage": {"input_tokens": 1000, "output_tokens": 0}}).encode()
        return R()

    def close(self):
        pass


def test_typesafe_direct_request_and_cost(monkeypatch):
    import http.client

    from framebudget import jev

    monkeypatch.setattr(http.client, "HTTPSConnection", FakeConnection)
    FakeConnection.sent.clear()
    r = jev.JevClient("k", provider="typesafe").decide("state")
    host, path, body, headers = FakeConnection.sent[0]
    assert (host, path, body["model"]) == ("api.typesafe.ai", "/v1/systemone", "jev-1.13.0")
    assert headers["Authorization"] == "Bearer k"
    assert r.ok and r.decision.count == 5 and abs(r.cost - 1000 * 0.042 / 1e6) < 1e-12


def test_provider_follows_the_key(monkeypatch, tmp_path):
    from framebudget import jev

    monkeypatch.chdir(tmp_path)
    for k in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "JEV_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    assert jev.detect_provider() == "openrouter" and jev.load_api_key() == "or"
    (tmp_path / ".env").write_text("TYPESAFE_API_KEY=ts\n")
    assert jev.detect_provider() == "typesafe" and jev.load_api_key() == "ts"
