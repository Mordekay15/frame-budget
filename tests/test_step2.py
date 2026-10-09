from framebudget.decision import Decision
from framebudget.game import DEFAULT_DECISION
from framebudget.sim import FixedDifficulty, run_episode


def test_same_seed_same_game():
    a = run_episode(FixedDifficulty(DEFAULT_DECISION), "medium", 7).row()
    b = run_episode(FixedDifficulty(DEFAULT_DECISION), "medium", 7).row()
    assert a == b


def test_weak_dies_strong_is_bored():
    weak = [run_episode(FixedDifficulty(DEFAULT_DECISION), "weak", s) for s in range(20)]
    strong = [run_episode(FixedDifficulty(DEFAULT_DECISION), "strong", s) for s in range(20)]
    assert sum(r.died for r in weak) >= 18
    assert sum(r.died for r in strong) == 0
    assert sum(r.experience["bored"] for r in strong) / 20 > 0.7


def test_bigger_waves_hurt_more():
    easy = run_episode(FixedDifficulty(Decision(3, 0.75)), "medium", 1)
    hard = run_episode(FixedDifficulty(Decision(12, 1.5)), "medium", 1)
    assert hard.died and not easy.died
