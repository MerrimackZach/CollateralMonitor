"""Glue between the database and the engine."""
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AdvanceRate, ConcentrationLimit, Facility, Firm
from engine.inputs import CaseInput


@dataclass(frozen=True)
class FacilityTerms:
    commitment: Decimal
    outstanding: Decimal
    min_coverage_ratio: Decimal
    advance_rates: dict[str, Decimal]
    concentration_limits: dict[str, Decimal]


def _get_firm(session: Session, firm_name: str) -> Firm:
    firm = session.scalar(select(Firm).where(Firm.name == firm_name))
    if firm is None:
        raise ValueError(f"No firm named {firm_name!r}")
    return firm


def load_case_inputs(session: Session, firm_name: str) -> list[CaseInput]:
    """Load a firm's cases as engine inputs. The engine never sees database objects."""
    firm = _get_firm(session, firm_name)
    return [
        CaseInput(
            case_type=c.case_type,
            stage=c.stage,
            filed_date=c.filed_date,
            projected_fee=c.projected_fee,
            jurisdiction=c.jurisdiction,
        )
        for c in firm.cases
    ]


def load_facility_terms(session: Session, firm_name: str) -> FacilityTerms:
    """Load a firm's credit terms. Assumes one facility per firm for now."""
    firm = _get_firm(session, firm_name)
    facility = session.scalar(select(Facility).where(Facility.firm_id == firm.id))
    if facility is None:
        raise ValueError(f"{firm_name!r} has no facility")

    rates = session.scalars(
        select(AdvanceRate).where(AdvanceRate.facility_id == facility.id)
    ).all()
    limits = session.scalars(
        select(ConcentrationLimit).where(ConcentrationLimit.facility_id == facility.id)
    ).all()

    return FacilityTerms(
        commitment=facility.commitment_amount,
        outstanding=facility.outstanding_balance,
        min_coverage_ratio=facility.min_coverage_ratio,
        advance_rates={r.case_type: r.advance_rate for r in rates},
        concentration_limits={lim.category: lim.max_share for lim in limits},
    )
