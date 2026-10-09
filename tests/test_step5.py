from framebudget.arch import AsyncFallback
from framebudget.channel import SimChannel, ThreadChannel
from framebudget.clock import RealClock
from framebudget.decision import DecisionState
from framebudget.deciders import FakeAnswers, SimulatedJev
from framebudget.sim import run_episode


class ConstLatency:
    def __init__(self, ms):
        self.ms = ms

    def sample_ms(self):
        return self.ms


def arch(latency_ms, budget):
    return AsyncFallback(SimChannel(SimulatedJev(FakeAnswers(0), ConstLatency(latency_ms))), budget)


def test_fast_answers_are_used():
    r = run_episode(arch(80, 100), "medium", 0)
    assert r.row()["deadline_met"] == 1.0 and r.row()["fallback_rate"] == 0.0
    assert r.ticks["overruns"] == 0 and r.ticks["period_max_ms"] <= 33.0 + 1e-9


def test_slow_answers_fall_back_to_rules():
    r = run_episode(arch(300, 100), "medium", 0)
    assert r.row()["deadline_met"] == 0.0 and r.row()["fallback_rate"] == 1.0
    assert r.extra["late"] >= len(r.events) - 1  # the last request may outlive the game


def test_answer_after_wave_spawned_is_stale():
    # The pause between waves is 1 s: an answer after 1.5 s can no longer apply.
    r = run_episode(arch(1500, 5000), "medium", 0)
    assert r.extra["stale"] > 0 and r.row()["deadline_met"] == 0.0


def test_thread_channel_does_not_block():
    clock = RealClock()
    ch = ThreadChannel(lambda: SimulatedJev(FakeAnswers(0), ConstLatency(100)), clock)
    s = DecisionState(50, 100, 3, 5, 1.0, 20, 3.0, 5.0, 1.6)
    t0 = clock.now()
    ch.submit(1, s, t0)
    assert clock.now() - t0 < 0.02  # returned immediately
    assert ch.poll(clock.now()) == []
    clock.sleep_until(t0 + 0.3)
    got = ch.poll(clock.now())
    ch.close()
    assert len(got) == 1 and 90 <= got[0].elapsed_ms <= 250
