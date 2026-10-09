from framebudget.arch import AsyncFallback, PrefetchAsync
from framebudget.channel import SimChannel
from framebudget.deciders import FakeAnswers, SimulatedJev
from framebudget.sim import run_episode


def test_prefetch_beats_async_at_a_tight_deadline():
    def mean_met(make):
        rows = [run_episode(make(SimChannel(SimulatedJev(FakeAnswers(s)))), "medium", s).row()
                for s in range(10)]
        return sum(r["deadline_met"] for r in rows) / len(rows)

    assert mean_met(lambda ch: PrefetchAsync(ch, 33, coarse=2)) > mean_met(lambda ch: AsyncFallback(ch, 33)) + 0.1


def test_prefetch_predicts_three_states_and_counts_requests():
    arch = PrefetchAsync(SimChannel(SimulatedJev(FakeAnswers(0))), 100)
    r = run_episode(arch, "strong", 0)
    assert r.extra["prefetch_requests"] > 0
    assert r.extra["prefetch_used"] <= r.extra["prefetch_requests"]
    assert any(e.applied.source == "prefetch" for e in r.events) or r.extra["prefetch_used"] == 0
