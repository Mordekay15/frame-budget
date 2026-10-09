from framebudget.arch import CachedAsync
from framebudget.cache import signature
from framebudget.channel import SimChannel
from framebudget.decision import DecisionState
from framebudget.deciders import FakeAnswers, SimulatedJev
from framebudget.sim import run_episode


def st(health, dmg=20.0, clear=3.0):
    return DecisionState(health, 100, 3, 5, 1.0, dmg, clear, 5.0, 1.6)


def test_coarser_signature_merges_more_states():
    a, b = st(61), st(68)
    assert signature(a, 0.25) != signature(b, 0.25)
    assert signature(a, 1) == signature(b, 1)


def test_cache_hits_skip_the_request():
    cache = {}
    jev = SimulatedJev(FakeAnswers(0, noise=0))
    first = run_episode(CachedAsync(SimChannel(jev), 250, coarse=8, cache=cache), "medium", 0)
    second = run_episode(CachedAsync(SimChannel(jev), 250, coarse=8, cache=cache), "medium", 1)
    assert second.extra["hits"] > first.extra["hits"]
    assert second.row()["requests"] < first.row()["requests"]
    hits = [e for e in second.events if e.cache_hit]
    assert hits and all(e.in_time and not e.requested and e.applied.source == "cache" for e in hits)


def test_late_answers_still_fill_the_cache():
    class Slow:
        def sample_ms(self):
            return 600.0

    a = CachedAsync(SimChannel(SimulatedJev(FakeAnswers(0), Slow())), 100, coarse=4)
    r = run_episode(a, "medium", 0)
    assert r.extra["late"] > 0 and len(a.cache) > 0 and r.extra["hits"] > 0
