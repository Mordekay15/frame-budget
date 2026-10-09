from framebudget.arch import Blocking
from framebudget.clock import SimClock
from framebudget.decision import DecisionState
from framebudget.deciders import Answer, FakeAnswers, RuleDecider, SimulatedJev, charge_latency
from framebudget.sim import run_episode


class ConstLatency:
    def __init__(self, ms):
        self.ms = ms

    def sample_ms(self):
        return self.ms


def test_every_decider_has_the_same_interface():
    s = DecisionState(50, 100, 3, 5, 1.0, 20, 3.0, 5.0, 1.6)
    for d in (RuleDecider(), SimulatedJev()):
        a = d.decide(s)
        assert isinstance(a, Answer) and a.ok and a.decision.count in (3, 5, 8, 12)


def test_blocking_blows_out_tick_by_latency():
    arch = Blocking(SimulatedJev(FakeAnswers(0), ConstLatency(330)))
    r = run_episode(arch, "medium", 0)
    assert abs(r.ticks["period_max_ms"] - 330) < 1e-6
    assert abs(r.ticks["blowout_factor"] - 10) < 1e-6
    assert r.ticks["overruns"] == len(r.events)
    assert all(e.applied.source == "jev" for e in r.events)


def test_failed_request_falls_back_to_rules():
    arch = Blocking(SimulatedJev(FakeAnswers(0), ConstLatency(float("inf"))))
    r = run_episode(arch, "medium", 0, waves=3)
    assert all(e.fallback and e.applied.source == "rules" for e in r.events)


def test_charge_latency_moves_sim_clock():
    c = SimClock()
    charge_latency(c, RuleDecider(), 250)
    assert abs(c.now() - 0.25) < 1e-12


def test_fake_answers_ease_off_when_hurt():
    fa = FakeAnswers(noise=0)
    hurt = fa.answer(DecisionState(15, 100, 3, 5, 1.0, 40, 3.0, 9.0, 1.6), "")[0]
    fine = fa.answer(DecisionState(100, 100, 3, 5, 1.0, 5, 2.0, 2.0, 2.5), "")[0]
    assert hurt.count * hurt.mult < fine.count * fine.mult
