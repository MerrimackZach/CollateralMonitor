"""Glue between the database and the engine."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Firm
from engine.inputs import CaseInput


def load_case_inputs(session: Session, firm_name: str) -> list[CaseInput]:
    """Load a firm's cases as engine inputs. The engine never sees database objects."""
    firm = session.scalar(select(Firm).where(Firm.name == firm_name))
    if firm is None:
        raise ValueError(f"No firm named {firm_name!r}")
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
