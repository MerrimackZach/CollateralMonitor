"""Load synthetic demo portfolios into Postgres. Safe to re-run."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AdvanceRate, Case, ConcentrationLimit, Facility, Firm
from app.synthetic import PROFILES, generate_cases

FACILITY_TERMS = {
    "Demo Firm Alpha": {"commitment": "3000000", "outstanding": "1500000"},
    "Demo Firm Bravo": {"commitment": "5000000", "outstanding": "3000000"},
    "Demo Firm Charlie": {"commitment": "12000000", "outstanding": "8000000"},
}

ADVANCE_RATES = {"mass_tort": "0.30", "class_action": "0.35", "pi": "0.45"}

CONCENTRATION_LIMITS = {
    "mass_tort": "0.60",
    "class_action": "0.60",
    "pi": "0.60",
    "single_case": "0.10",
    "per_jurisdiction": "0.25",
}


def ensure_limits(session: Session, facility_id: int) -> None:
    """Add any concentration limits the facility is missing."""
    existing = set(
        session.scalars(
            select(ConcentrationLimit.category).where(
                ConcentrationLimit.facility_id == facility_id
            )
        )
    )
    for category, share in CONCENTRATION_LIMITS.items():
        if category not in existing:
            session.add(
                ConcentrationLimit(
                    facility_id=facility_id,
                    category=category,
                    max_share=Decimal(share),
                )
            )


def seed() -> None:
    with SessionLocal() as session:
        for name, profile in PROFILES.items():
            firm = session.scalar(select(Firm).where(Firm.name == name))
            if firm is not None:
                facility = session.scalar(
                    select(Facility).where(Facility.firm_id == firm.id)
                )
                ensure_limits(session, facility.id)
                session.commit()
                print(f"{name}: already seeded, limits checked")
                continue

            firm = Firm(name=name, state=profile["state"])
            session.add(firm)
            session.flush()  # assigns firm.id

            terms = FACILITY_TERMS[name]
            facility = Facility(
                firm_id=firm.id,
                commitment_amount=Decimal(terms["commitment"]),
                outstanding_balance=Decimal(terms["outstanding"]),
            )
            session.add(facility)
            session.flush()  # assigns facility.id

            for case_type, rate in ADVANCE_RATES.items():
                session.add(
                    AdvanceRate(
                        facility_id=facility.id,
                        case_type=case_type,
                        advance_rate=Decimal(rate),
                    )
                )
            ensure_limits(session, facility.id)

            records = generate_cases(profile["counts"], seed=profile["seed"])
            session.add_all(
                Case(
                    firm_id=firm.id,
                    case_type=r.case_type,
                    stage=r.stage,
                    filed_date=r.filed_date,
                    projected_fee=r.projected_fee,
                    jurisdiction=r.jurisdiction,
                )
                for r in records
            )
            session.commit()
            print(f"{name}: seeded {len(records)} cases")


if __name__ == "__main__":
    seed()
