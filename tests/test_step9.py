from framebudget.experiment import Setup, cells
from scripts.step9_run_experiments import run_cell
from scripts.step9_consistency import agreement, probe_states


def test_cells_cover_the_design():
    todo = list(cells(["rules", "async"], [33.0, 100.0], ["weak", "strong"], 3))
    assert len(todo) == 2 * 3 + 2 * 2 * 3  # rules has no deadline
    assert ("async", 100.0, "strong", 2) in todo and ("rules", None, "weak", 0) in todo


def test_a_cell_always_gives_the_same_row():
    setup = Setup()
    a = run_cell(setup, ("cache", 100.0, "medium", 4))
    b = run_cell(Setup(), ("cache", 100.0, "medium", 4))
    assert a == b and a["cost_per_hour_usd"] > 0


def test_common_random_numbers_same_game_for_rules_and_blocking_latency():
    s = Setup()
    l1 = [s.latency_model("weak", 3).sample_ms() for _ in range(1)]
    l2 = [s.latency_model("weak", 3).sample_ms() for _ in range(1)]
    assert l1 == l2


def test_agreement():
    assert agreement([1, 1, 2, 1]) == (0.75, 2)
    assert len(probe_states()) == 12


def test_record_then_replay_sweep(tmp_path):
    from framebudget.deciders import FakeAnswers
    from framebudget.replay import AnswerStore, StoreAnswers

    store = AnswerStore(tmp_path / "a.json")
    rec = Setup(StoreAnswers(store, fallback=FakeAnswers(noise=0)))
    todo = [("async", 250.0, "weak", 0), ("prefetch", 33.0, "strong", 1)]
    first = [run_cell(rec, c) for c in todo]
    store.save()
    strict = StoreAnswers(AnswerStore(tmp_path / "a.json"))
    second = [run_cell(Setup(strict), c) for c in todo]
    assert first == second and strict.misses == 0
