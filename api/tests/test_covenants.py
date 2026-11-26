from decimal import Decimal

from engine.borrowing_base import BorrowingBaseResult
from engine.covenants import check_covenants

MIN_RATIO = Decimal("1.50")


def base(counted, borrowing_base):
    zero = Decimal("0")
    return BorrowingBaseResult(
        total_present_value=Decimal(counted),
        counted_value=Decimal(counted),
        excluded_value=zero,
        borrowing_base=Decimal(borrowing_base),
        available_credit=zero,
        by_type={},
    )


def run(counted, borrowing_base, outstanding):
    return check_covenants(
        base(counted, borrowing_base),
        outstanding=Decimal(outstanding),
        min_coverage_ratio=MIN_RATIO,
    )


def test_ratio_above_minimum_passes():
    r = run("300000", "120000", "100000")
    assert r.coverage_ratio == Decimal("3.00")
    assert not r.coverage_breached


def test_exactly_at_minimum_is_not_a_breach():
    r = run("150000", "60000", "100000")
    assert r.coverage_ratio == Decimal("1.50")
    assert not r.coverage_breached


def test_below_minimum_is_a_breach():
    r = run("140000", "60000", "100000")
    assert r.coverage_ratio == Decimal("1.40")
    assert r.coverage_breached


def test_nothing_outstanding_means_no_ratio_and_no_breach():
    r = run("300000", "120000", "0")
    assert r.coverage_ratio is None
    assert not r.coverage_breached
    assert r.borrowing_base_deficiency == Decimal("0")


def test_deficiency_when_outstanding_exceeds_base():
    r = run("300000", "80000", "100000")
    assert r.borrowing_base_deficiency == Decimal("20000")


def test_no_deficiency_when_base_covers_outstanding():
    r = run("300000", "120000", "100000")
    assert r.borrowing_base_deficiency == Decimal("0")


def test_can_be_over_advanced_while_passing_coverage():
    # Coverage 3.0x passes, yet the base (80k) is below what is owed (100k).
    r = run("300000", "80000", "100000")
    assert not r.coverage_breached
    assert r.borrowing_base_deficiency > 0
