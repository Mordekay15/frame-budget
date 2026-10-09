from framebudget.clock import RealClock, SimClock
from framebudget.loop import TICK_S, run_loop, tick_summary


def test_sim_loop_is_exact():
    recs = run_loop(lambda i: None, SimClock(), n_ticks=100)
    s = tick_summary(recs)
    assert s["ticks"] == 100 and abs(s["final_drift_ms"]) < 1e-9
    assert abs(s["period_max_ms"] - TICK_S * 1000) < 1e-9


def test_sim_overrun_shows_up_as_blowout():
    clock = SimClock()
    recs = run_loop(lambda i: clock.wait(0.2) if i == 5 else None, clock, n_ticks=20)
    s = tick_summary(recs)
    assert s["overruns"] == 1
    assert abs(s["period_max_ms"] - 200) < 1e-6  # tick 6 starts 200 ms after tick 5


def test_real_loop_has_no_cumulative_drift():
    recs = run_loop(lambda i: None, RealClock(), n_ticks=30)
    assert abs(tick_summary(recs)["final_drift_ms"]) < 5


def test_loop_stops_when_tick_returns_true():
    recs = run_loop(lambda i: i == 9, SimClock())
    assert len(recs) == 10
