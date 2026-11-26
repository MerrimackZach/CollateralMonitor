from dataclasses import dataclass
from decimal import Decimal

from engine.inputs import CaseInput
from engine.valuation import CaseValuation

CENTS = Decimal("0.01")
SINGLE_CASE = "single_case"  # key for the single-case limit
PER_JURISDICTION = "per_jurisdiction"  # key for the per-jurisdiction limit


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
    """See docs/assumptions.md, 'Borrowing base rules' and 'Jurisdiction cap'."""
    if len(cases) != len(valuations):
        raise ValueError("cases and valuations must be the same length")

    zero = Decimal("0")
    total_pv = sum((v.present_value for v in valuations), zero)

    single_cap = None
    if SINGLE_CASE in concentration_limits:
        single_cap = concentration_limits[SINGLE_CASE] * total_pv

    # Step 1: per-case counted value. Ineligible types count for nothing, and
    # the single-case cap trims any one case that is too large.
    counted: list[Decimal] = []
    for case, val in zip(cases, valuations):
        if case.case_type not in advance_rates:
            counted.append(zero)
        elif single_cap is not None:
            counted.append(min(val.present_value, single_cap))
        else:
            counted.append(val.present_value)

    # Step 2: jurisdiction cap. Every case in an over-cap jurisdiction is
    # reduced by the same percentage.
    if PER_JURISDICTION in concentration_limits:
        jurisdiction_cap = concentration_limits[PER_JURISDICTION] * total_pv
        by_jurisdiction: dict[str, Decimal] = {}
        for case, value in zip(cases, counted):
            by_jurisdiction[case.jurisdiction] = (
                by_jurisdiction.get(case.jurisdiction, zero) + value
            )
        counted = [
            value * jurisdiction_cap / by_jurisdiction[case.jurisdiction]
            if by_jurisdiction[case.jurisdiction] > jurisdiction_cap
            else value
            for case, value in zip(cases, counted)
        ]

    # Step 3: group by case type, apply the type cap and the advance rate.
    pv_by_type: dict[str, Decimal] = {}
    counted_by_type: dict[str, Decimal] = {}
    for case, val, value in zip(cases, valuations, counted):
        pv_by_type[case.case_type] = (
            pv_by_type.get(case.case_type, zero) + val.present_value
        )
        counted_by_type[case.case_type] = (
            counted_by_type.get(case.case_type, zero) + value
        )

    by_type: dict[str, TypeBreakdown] = {}
    total_counted = zero
    total_base = zero
    for case_type, pv in pv_by_type.items():
        rate = advance_rates.get(case_type, zero)  # ineligible types already count 0
        type_counted = counted_by_type[case_type]
        if case_type in concentration_limits:
            type_counted = min(type_counted, concentration_limits[case_type] * total_pv)
        base = type_counted * rate
        by_type[case_type] = TypeBreakdown(
            present_value=pv.quantize(CENTS),
            counted_value=type_counted.quantize(CENTS),
            borrowing_base=base.quantize(CENTS),
        )
        total_counted += type_counted
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
