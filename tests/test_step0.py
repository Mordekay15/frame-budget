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
