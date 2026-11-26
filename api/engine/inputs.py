from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class CaseInput:
    """What the engine needs to know about one case. No database types here."""

    case_type: str
    stage: str
    filed_date: date
    projected_fee: Decimal
    jurisdiction: str
