import pytest

from framebudget.arch import AsyncFallback
from framebudget.channel import SimChannel
from framebudget.deciders import FakeAnswers, SimulatedJev
from framebudget.latency import LognormalLatency
from framebudget.replay import AnswerStore, MissingAnswer, RecordedLatency, RecordingDecider, StoreAnswers
from framebudget.sim import run_episode


def run(decider, seeds=range(3)):
    return [run_episode(AsyncFallback(SimChannel(decider), 250), "medium", s).row() for s in seeds]


def test_record_then_replay_is_identical(tmp_path):
    store = AnswerStore(tmp_path / "answers.json")
    rec = RecordingDecider(SimulatedJev(FakeAnswers(1), LognormalLatency(seed=1)), tmp_path / "lat.csv", store)
    recorded = run(rec)
    rec.close()

    def replay():
        return run(SimulatedJev(StoreAnswers(AnswerStore(tmp_path / "answers.json")),
                                RecordedLatency(tmp_path / "lat.csv")))

    assert replay() == replay() == recorded


def test_strict_replay_refuses_unknown_states(tmp_path):
    src = StoreAnswers(AnswerStore())
    with pytest.raises(MissingAnswer):
        run(SimulatedJev(src, LognormalLatency()), seeds=[0])


def test_recorded_latency_wraps_and_offsets(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("latency_ms,ok\n10,1\n20,1\n30,0\n")
    r = RecordedLatency(p, offset=1)
    assert [r.sample_ms() for _ in range(4)] == [20.0, float("inf"), 10.0, 20.0]
