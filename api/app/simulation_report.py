"""Print Monte Carlo results for every seeded firm under three correlation settings."""
import time

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Firm
from app.services import load_case_inputs, load_facility_terms
from engine.simulation import build_sim_cases, simulate_portfolio
from engine.transition import LookupTransitionModel
from engine.valuation import DEFAULT_DISCOUNT_RATE, value_portfolio

N_SCENARIOS = 10_000
SEED = 42

# Illustrative assumptions, not estimates from data. PI cases are single
# events and are treated as independent, so they are left out.
CORRELATION_SCENARIOS = {
    "independent": {},
    "moderate": {"mass_tort": 0.30, "class_action": 0.20},
    "high": {"mass_tort": 0.60, "class_action": 0.40},
}


def main() -> None:
    model = LookupTransitionModel()
    rate = float(DEFAULT_DISCOUNT_RATE)
    start = time.perf_counter()
    runs = 0
    with SessionLocal() as session:
        names = session.scalars(select(Firm.name).order_by(Firm.name)).all()
        for name in names:
            cases = load_case_inputs(session, name)
            terms = load_facility_terms(session, name)
            outstanding = float(terms.outstanding)
            phase2_pv = value_portfolio(cases, model).total_present_value
            sim_cases = build_sim_cases(cases, model)

            print(name)
            print(f"  phase 2 value ${phase2_pv:,.0f}   outstanding ${outstanding:,.0f}")
            print(
                f"  {'scenario':<12}{'mean':>13}{'P10':>13}"
                f"{'P50':>13}{'P90':>13}{'shortfall':>11}"
            )
            for label, correlations in CORRELATION_SCENARIOS.items():
                r = simulate_portfolio(
                    sim_cases,
                    N_SCENARIOS,
                    SEED,
                    rate,
                    outstanding,
                    correlations=correlations,
                )
                runs += 1
                print(
                    f"  {label:<12}{r.mean:>13,.0f}{r.p10:>13,.0f}"
                    f"{r.p50:>13,.0f}{r.p90:>13,.0f}{r.shortfall_probability:>11.2%}"
                )
    elapsed = time.perf_counter() - start
    print(f"\n{runs} simulations of {N_SCENARIOS:,} scenarios in {elapsed:.2f}s (including database loads)")


if __name__ == "__main__":
    main()