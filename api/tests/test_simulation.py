from datetime import date
from decimal import Decimal

import numpy as np
import pytest

from engine.inputs import CaseInput
from engine.simulation import (
    SimCase,
    build_sim_cases,
    simulate_case,
    simulate_portfolio,
)
from engine.transition import LookupTransitionModel
from engine.valuation import value_case


def make_case(win_prob, fee=1_000_000, years=2.0):
    return SimCase("c1", win_prob, years, fee, fee, fee)


# --- single case ---

def test_certain_win_always_pays_something():
    values = simulate_case(make_case(1.0), 1000, np.random.default_rng(1), 0.12)
    assert (values > 0).all()
    assert (values <= 1_000_000).all()  # discounting can only shrink it


def test_certain_loss_always_pays_zero():
    values = simulate_case(make_case(0.0), 1000, np.random.default_rng(1), 0.12)
    assert (values == 0).all()


def test_same_seed_gives_identical_results():
    a = simulate_case(make_case(0.6), 1000, np.random.default_rng(7), 0.12)
    b = simulate_case(make_case(0.6), 1000, np.random.default_rng(7), 0.12)
    assert np.array_equal(a, b)


def test_win_rate_matches_probability():
    values = simulate_case(make_case(0.55), 200_000, np.random.default_rng(3), 0.12)
    assert abs((values > 0).mean() - 0.55) < 0.01


# --- portfolio ---

def test_portfolio_of_certain_losses_always_falls_short():
    r = simulate_portfolio([make_case(0.0), make_case(0.0)], 1000, 1, 0.12, 1.0)
    assert r.p10 == r.p50 == r.p90 == 0.0
    assert r.shortfall_probability == 1.0


def test_certain_wins_never_fall_short_of_small_balance():
    r = simulate_portfolio([make_case(1.0), make_case(1.0)], 1000, 1, 0.12, 1.0)
    assert r.shortfall_probability == 0.0
    assert r.p90 <= 2_000_000


def test_empty_portfolio_with_no_balance_has_no_shortfall():
    r = simulate_portfolio([], 1000, 1, 0.12, 0.0)
    assert r.shortfall_probability == 0.0


def test_same_seed_same_portfolio_result():
    cases = [make_case(0.6), make_case(0.4)]
    a = simulate_portfolio(cases, 5000, 42, 0.12, 500_000)
    b = simulate_portfolio(cases, 5000, 42, 0.12, 500_000)
    assert a == b


# --- adapter and cross-check against Phase 2 ---

MODEL = LookupTransitionModel()
CASE = CaseInput("mass_tort", "discovery", date(2024, 1, 1), Decimal("40000"), "NY")


def test_adapter_converts_outlook_and_fee():
    [sim] = build_sim_cases([CASE], MODEL)
    assert sim.win_prob == 0.65
    assert sim.mean_years == 3.5
    assert sim.fee_mode == 40000.0


def test_simulation_mean_is_close_to_phase_2_value():
    # Phase 2 hand-checked value for this case is about $17,487.
    pv = float(value_case(CASE, MODEL).present_value)
    r = simulate_portfolio(build_sim_cases([CASE], MODEL), 200_000, 5, 0.12, 0.0)
    assert pv * 0.99 <= r.mean <= pv * 1.05

# --- correlation (shared shock) ---

def both_win_rate(rho, n=100_000, seed=11):
    rng = np.random.default_rng(seed)
    shock = rng.standard_normal(n)
    case = make_case(0.5)
    a = simulate_case(case, n, rng, 0.12, shock=shock, correlation=rho)
    b = simulate_case(case, n, rng, 0.12, shock=shock, correlation=rho)
    return ((a > 0) & (b > 0)).mean()


def test_no_correlation_means_cases_win_independently():
    assert 0.23 < both_win_rate(0.0) < 0.27  # 0.5 x 0.5 = 0.25


def test_high_correlation_makes_cases_win_together():
    # For two coin-flip cases with rho 0.9, theory gives about 0.43.
    assert 0.41 < both_win_rate(0.9) < 0.45


def test_correlation_keeps_each_cases_win_rate():
    rng = np.random.default_rng(3)
    shock = rng.standard_normal(200_000)
    values = simulate_case(
        make_case(0.55), 200_000, rng, 0.12, shock=shock, correlation=0.6
    )
    assert abs((values > 0).mean() - 0.55) < 0.01


def test_correlation_widens_the_spread_but_keeps_the_mean():
    cases = [make_case(0.6, fee=10_000) for _ in range(100)]
    indep = simulate_portfolio(cases, 20_000, 1, 0.12, 0.0)
    corr = simulate_portfolio(
        cases, 20_000, 1, 0.12, 0.0, correlations={"default": 0.5}
    )
    assert abs(corr.mean - indep.mean) / indep.mean < 0.03
    assert (corr.p90 - corr.p10) > 2 * (indep.p90 - indep.p10)


def test_invalid_correlation_is_rejected():
    with pytest.raises(ValueError):
        simulate_portfolio(
            [make_case(0.5)], 100, 1, 0.12, 0.0, correlations={"default": 1.5}
        )