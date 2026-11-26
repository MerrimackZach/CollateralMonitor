from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from engine.inputs import CaseInput


@dataclass(frozen=True)
class StageOutlook:
    probability: Decimal  # chance of a recovery (win or settlement)
    years_remaining: Decimal  # expected time until resolution


class TransitionModel(Protocol):
    """Anything with an outlook() method can value cases.

    Swapping in a more refined model later means writing a new class like this
    one. The valuation code does not change.
    """

    def outlook(self, case: CaseInput) -> StageOutlook: ...


# Illustrative values from docs/assumptions.md
_PROBABILITY = {
    "mass_tort": {"filed": "0.55", "discovery": "0.65", "settlement_talks": "0.80"},
    "class_action": {"filed": "0.45", "discovery": "0.60", "settlement_talks": "0.75"},
    "pi": {"filed": "0.65", "discovery": "0.75", "settlement_talks": "0.88"},
}

_YEARS = {
    "mass_tort": {"filed": "5.0", "discovery": "3.5", "settlement_talks": "1.5"},
    "class_action": {"filed": "4.0", "discovery": "2.5", "settlement_talks": "1.0"},
    "pi": {"filed": "2.0", "discovery": "1.2", "settlement_talks": "0.5"},
}


class LookupTransitionModel:
    """Baseline model: probability and duration looked up by case type and stage."""

    def outlook(self, case: CaseInput) -> StageOutlook:
        try:
            return StageOutlook(
                probability=Decimal(_PROBABILITY[case.case_type][case.stage]),
                years_remaining=Decimal(_YEARS[case.case_type][case.stage]),
            )
        except KeyError:
            raise ValueError(
                f"No assumptions for {case.case_type!r} at stage {case.stage!r}"
            ) from None
