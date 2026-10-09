from framebudget.arch import RulesOnly
from framebudget.decision import DecisionState
from framebudget.game import DEFAULT_DECISION
from framebudget.rules import LADDER, HunickePolicy
from framebudget.sim import FixedDifficulty, run_episode


def state(health, dmg=20.0):
    return DecisionState(health, 100, 3, 5, 1.0, dmg, 3.0, 5.0, 1.6)


def test_ladder_goes_from_easy_to_hard():
    assert LADDER[0] == (3, 0.75) and LADDER[-1] == (12, 1.5) and len(LADDER) == 16


def test_low_health_makes_it_easier():
    p = HunickePolicy()
    start = p.level
    p.decide(state(15, dmg=40))
    assert p.level < start


def test_bored_player_gets_harder():
    p = HunickePolicy()
    start = p.level
    p.decide(state(100, dmg=3))
    assert p.level == start + 1


def test_peek_does_not_change_policy():
    p = HunickePolicy()
    before = (p.level, list(p._rates))
    p.peek(state(10, 50))
    assert (p.level, p._rates) == before


def test_rules_shift_deaths_and_boredom():
    def avg(make, skill, key):
        rs = [run_episode(make(), skill, s) for s in range(40)]
        return sum(getattr(r, "died") if key == "died" else r.experience[key] for r in rs) / 40

    fixed = lambda: FixedDifficulty(DEFAULT_DECISION)
    assert avg(RulesOnly, "weak", "died") < avg(fixed, "weak", "died") - 0.3
    assert avg(RulesOnly, "strong", "bored") < avg(fixed, "strong", "bored") - 0.3
