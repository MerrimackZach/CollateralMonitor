"""Synthetic portfolio generator. No database access: returns plain objects.

All numbers are illustrative; see docs/assumptions.md.
"""
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

# Fixed anchor date so seeded output is identical on every run.
ANCHOR_DATE = date(2026, 11, 25)

STAGES = ["filed", "discovery", "settlement_talks"]
STAGE_WEIGHTS = [0.40, 0.40, 0.20]

# How old a case typically is at each stage, in years (min, max).
AGE_YEARS = {
    "filed": (0.0, 1.0),
    "discovery": (1.0, 3.0),
    "settlement_talks": (2.0, 5.0),
}

# Projected fee range per case, in USD (low, high).
FEE_RANGES = {
    "mass_tort": (10_000, 80_000),
    "class_action": (500_000, 15_000_000),
    "pi": (15_000, 400_000),
}

JURISDICTIONS = ["NY", "CA", "TX", "FL", "IL", "NJ", "PA", "OH"]

# Three fictional demo firms with different sizes and risk profiles.
PROFILES = {
    "Demo Firm Alpha": {
        "state": "NY",
        "seed": 101,
        "counts": {"mass_tort": 40, "class_action": 3, "pi": 30},
    },
    "Demo Firm Bravo": {
        "state": "TX",
        "seed": 202,
        "counts": {"mass_tort": 250, "class_action": 2, "pi": 40},
    },
    "Demo Firm Charlie": {
        "state": "CA",
        "seed": 303,
        "counts": {"mass_tort": 120, "class_action": 8, "pi": 200},
    },
}


@dataclass(frozen=True)
class CaseRecord:
    case_type: str
    stage: str
    filed_date: date
    projected_fee: Decimal
    jurisdiction: str


def generate_cases(counts: dict[str, int], seed: int) -> list[CaseRecord]:
    """Generate synthetic cases. The same seed always gives the same result."""
    rng = random.Random(seed)
    cases = []
    for case_type, n in counts.items():
        low, high = FEE_RANGES[case_type]
        for _ in range(n):
            stage = rng.choices(STAGES, weights=STAGE_WEIGHTS)[0]
            min_age, max_age = AGE_YEARS[stage]
            age_days = int(rng.uniform(min_age, max_age) * 365)
            # Log scale: many small fees, a few large ones.
            fee = math.exp(rng.uniform(math.log(low), math.log(high)))
            cases.append(
                CaseRecord(
                    case_type=case_type,
                    stage=stage,
                    filed_date=ANCHOR_DATE - timedelta(days=age_days),
                    projected_fee=Decimal(str(round(fee, 2))),
                    jurisdiction=rng.choice(JURISDICTIONS),
                )
            )
    return cases


if __name__ == "__main__":
    for name, profile in PROFILES.items():
        cases = generate_cases(profile["counts"], seed=profile["seed"])
        total = sum(c.projected_fee for c in cases)
        print(f"{name}: {len(cases)} cases, total projected fee ${total:,.0f}")
        for case_type in profile["counts"]:
            subset = [c for c in cases if c.case_type == case_type]
            subtotal = sum(c.projected_fee for c in subset)
            print(f"    {case_type}: {len(subset)} cases, ${subtotal:,.0f}")
