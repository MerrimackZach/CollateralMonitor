from dataclasses import dataclass
from decimal import Decimal

from engine.borrowing_base import BorrowingBaseResult

RATIO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class CovenantResult:
    coverage_ratio: Decimal | None  # None when nothing is outstanding
    min_coverage_ratio: Decimal
    coverage_breached: bool
    borrowing_base_deficiency: Decimal  # how far outstanding exceeds the base


def check_covenants(
    base: BorrowingBaseResult,
    *,
    outstanding: Decimal,
    min_coverage_ratio: Decimal,
) -> CovenantResult:
    """See docs/assumptions.md, 'Covenant rules'."""
    zero = Decimal("0")
    deficiency = max(zero, outstanding - base.borrowing_base)

    if outstanding <= zero:
        return CovenantResult(
            coverage_ratio=None,
            min_coverage_ratio=min_coverage_ratio,
            coverage_breached=False,
            borrowing_base_deficiency=zero,
        )

    ratio = base.counted_value / outstanding
    return CovenantResult(
        coverage_ratio=ratio.quantize(RATIO_PLACES),
        min_coverage_ratio=min_coverage_ratio,
        # Compare the unrounded ratio so rounding can't hide or invent a breach.
        coverage_breached=ratio < min_coverage_ratio,
        borrowing_base_deficiency=deficiency.quantize(Decimal("0.01")),
    )
