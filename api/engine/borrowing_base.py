from dataclasses import dataclass
from decimal import Decimal

from engine.inputs import CaseInput
from engine.valuation import CaseValuation

CENTS = Decimal("0.01")
SINGLE_CASE = "single_case"  # the key used for the single-case limit


@dataclass(frozen=True)
class TypeBreakdown:
    present_value: Decimal  # value before any caps
    counted_value: Decimal  # value counted after caps and eligibility
    borrowing_base: Decimal  # counted value x advance rate


@dataclass(frozen=True)
class BorrowingBaseResult:
    total_present_value: Decimal
    counted_value: Decimal
    excluded_value: Decimal
    borrowing_base: Decimal
    available_credit: Decimal
    by_type: dict[str, TypeBreakdown]


def compute_borrowing_base(
    cases: list[CaseInput],
    valuations: list[CaseValuation],
    *,
    advance_rates: dict[str, Decimal],
    concentration_limits: dict[str, Decimal],
    commitment: Decimal,
    outstanding: Decimal,
) -> BorrowingBaseResult:
    """See docs/assumptions.md, 'Borrowing base rules'."""
    if len(cases) != len(valuations):
        raise ValueError("cases and valuations must be the same length")

    zero = Decimal("0")
    total_pv = sum((v.present_value for v in valuations), zero)

    single_cap = None
    if SINGLE_CASE in concentration_limits:
        single_cap = concentration_limits[SINGLE_CASE] * total_pv

    pv_by_type: dict[str, Decimal] = {}
    counted_by_type: dict[str, Decimal] = {}
    for case, val in zip(cases, valuations):
        pv = val.present_value
        counted = min(pv, single_cap) if single_cap is not None else pv
        pv_by_type[case.case_type] = pv_by_type.get(case.case_type, zero) + pv
        counted_by_type[case.case_type] = (
            counted_by_type.get(case.case_type, zero) + counted
        )

    by_type: dict[str, TypeBreakdown] = {}
    total_counted = zero
    total_base = zero
    for case_type, pv in pv_by_type.items():
        rate = advance_rates.get(case_type)
        if rate is None:
            counted, rate = zero, zero  # no advance rate means ineligible
        else:
            counted = counted_by_type[case_type]
            if case_type in concentration_limits:
                counted = min(counted, concentration_limits[case_type] * total_pv)
        base = counted * rate
        by_type[case_type] = TypeBreakdown(
            present_value=pv.quantize(CENTS),
            counted_value=counted.quantize(CENTS),
            borrowing_base=base.quantize(CENTS),
        )
        total_counted += counted
        total_base += base

    borrowing_base = total_base.quantize(CENTS)
    available = max(zero, min(borrowing_base, commitment) - outstanding)
    return BorrowingBaseResult(
        total_present_value=total_pv.quantize(CENTS),
        counted_value=total_counted.quantize(CENTS),
        excluded_value=(total_pv - total_counted).quantize(CENTS),
        borrowing_base=borrowing_base,
        available_credit=available.quantize(CENTS),
        by_type=by_type,
    )
