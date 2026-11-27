import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

from engine.inputs import CaseInput
from engine.transition import TransitionModel

_NORMAL = NormalDist()  # standard normal distribution, from the standard library


@dataclass(frozen=True)
class SimCase:
    case_id: str
    win_prob: float     # chance of any recovery (win or settlement)
    mean_years: float   # expected time until resolution
    fee_low: float
    fee_mode: float     # most likely fee
    fee_high: float
    group: str = "default"  # cases in the same group share one luck shock


DURATION_SIGMA = 0.5  # how spread out resolution times are


def _win_cutoff(win_prob: float) -> float:
    """A case wins when its luck score falls below this cutoff.

    The cutoff is chosen so that exactly win_prob of all possible luck
    scores fall below it.
    """
    if win_prob <= 0.0:
        return -math.inf  # never wins
    if win_prob >= 1.0:
        return math.inf  # always wins
    return _NORMAL.inv_cdf(win_prob)


def simulate_case(
    case: SimCase,
    n_scenarios: int,
    rng: np.random.Generator,
    annual_discount_rate: float,
    shock: np.ndarray | None = None,
    correlation: float = 0.0,
) -> np.ndarray:
    """Return one present value per scenario (array of length n_scenarios)."""
    own_luck = rng.standard_normal(n_scenarios)
    if shock is None or correlation == 0.0:
        luck = own_luck
    else:
        # Mix the group's shared luck with this case's own luck.
        luck = math.sqrt(correlation) * shock + math.sqrt(1.0 - correlation) * own_luck
    won = luck < _win_cutoff(case.win_prob)

    # Resolution time: lognormal, centered so the average equals mean_years
    mu = np.log(case.mean_years) - DURATION_SIGMA**2 / 2
    years = rng.lognormal(mu, DURATION_SIGMA, n_scenarios)

    if case.fee_low == case.fee_high:
        fees = np.full(n_scenarios, case.fee_mode)
    else:
        fees = rng.triangular(case.fee_low, case.fee_mode, case.fee_high, n_scenarios)

    discount = (1 + annual_discount_rate) ** (-years)
    return np.where(won, fees * discount, 0.0)


@dataclass(frozen=True)
class SimulationResult:
    n_scenarios: int
    seed: int
    mean: float
    p10: float
    p50: float
    p90: float
    outstanding_balance: float
    shortfall_probability: float


def simulate_portfolio(
    cases: list[SimCase],
    n_scenarios: int,
    seed: int,
    annual_discount_rate: float,
    outstanding_balance: float,
    correlations: dict[str, float] | None = None,
) -> SimulationResult:
    """correlations maps a group name to its rho (0 to 1). Missing groups get 0."""
    correlations = correlations or {}
    for group, rho in correlations.items():
        if not 0.0 <= rho <= 1.0:
            raise ValueError(f"correlation for {group!r} must be 0 to 1, got {rho}")

    rng = np.random.default_rng(seed)  # one generator for the whole run

    shocks: dict[str, np.ndarray] = {}  # one shared shock per group
    totals = np.zeros(n_scenarios)  # portfolio value in each scenario
    for case in cases:
        if case.group not in shocks:
            shocks[case.group] = rng.standard_normal(n_scenarios)
        totals += simulate_case(
            case,
            n_scenarios,
            rng,
            annual_discount_rate,
            shock=shocks[case.group],
            correlation=correlations.get(case.group, 0.0),
        )

    p10, p50, p90 = np.percentile(totals, [10, 50, 90])
    shortfall = float((totals < outstanding_balance).mean())

    return SimulationResult(
        n_scenarios=n_scenarios,
        seed=seed,
        mean=float(totals.mean()),
        p10=float(p10),
        p50=float(p50),
        p90=float(p90),
        outstanding_balance=outstanding_balance,
        shortfall_probability=shortfall,
    )


def build_sim_cases(cases: list[CaseInput], model: TransitionModel) -> list[SimCase]:
    """Convert engine inputs into simulation inputs using any TransitionModel."""
    sim_cases = []
    for i, case in enumerate(cases):
        outlook = model.outlook(case)
        fee = float(case.projected_fee)  # Decimal -> float, once, at the boundary
        sim_cases.append(
            SimCase(
                case_id=str(i),
                win_prob=float(outlook.probability),
                mean_years=float(outlook.years_remaining),
                fee_low=fee,
                fee_mode=fee,
                fee_high=fee,
                group=case.case_type,  # mass torts shocked together, etc.
            )
        )
    return sim_cases