from datetime import date
from decimal import Decimal

import pytest

from engine.borrowing_base import compute_borrowing_base
from engine.inputs import CaseInput
from engine.valuation import CaseValuation


def make(case_type):
    return CaseInput(
        case_type=case_type,
        stage="discovery",
        filed_date=date(2024, 1, 1),
        projected_fee=Decimal("1"),
        jurisdiction="NY",
    )


def val(pv):
    return CaseValuation(expected_fee=Decimal(pv), present_value=Decimal(pv))


CASES = [make("pi"), make("pi"), make("class_action")]
VALS = [val("100000"), val("100000"), val("300000")]
RATES = {"pi": Decimal("0.5"), "class_action": Decimal("0.4")}


def run(
    limits=None,
    commitment="1000000",
    outstanding="100000",
    rates=None,
    cases=None,
    vals=None,
):
    return compute_borrowing_base(
        CASES if cases is None else cases,
        VALS if vals is None else vals,
        advance_rates=RATES if rates is None else rates,
        concentration_limits=limits or {},
        commitment=Decimal(commitment),
        outstanding=Decimal(outstanding),
    )


def test_no_limits():
    # pi: 200k x 0.5 = 100k; class action: 300k x 0.4 = 120k
    r = run()
    assert r.borrowing_base == Decimal("220000")
    assert r.available_credit == Decimal("120000")
    assert r.excluded_value == Decimal("0")


def test_single_case_limit_trims_the_big_case():
    # cap = 30% x 500k = 150k, so the class action counts 150k, not 300k
    r = run(limits={"single_case": Decimal("0.30")})
    assert r.by_type["class_action"].counted_value == Decimal("150000")
    assert r.borrowing_base == Decimal("160000")  # 100k + 150k x 0.4
    assert r.excluded_value == Decimal("150000")
    assert r.available_credit == Decimal("60000")


def test_case_type_limit():
    # class action capped at 40% x 500k = 200k
    r = run(limits={"class_action": Decimal("0.40")})
    assert r.by_type["class_action"].counted_value == Decimal("200000")
    assert r.borrowing_base == Decimal("180000")  # 100k + 200k x 0.4


def test_commitment_caps_available_credit():
    r = run(commitment="150000")
    assert r.borrowing_base == Decimal("220000")
    assert r.available_credit == Decimal("50000")  # 150k - 100k


def test_outstanding_above_base_gives_zero_available():
    r = run(outstanding="300000")
    assert r.available_credit == Decimal("0")


def test_case_type_without_advance_rate_is_ineligible():
    r = run(rates={"pi": Decimal("0.5")})
    assert r.by_type["class_action"].counted_value == Decimal("0")
    assert r.borrowing_base == Decimal("100000")
    assert r.excluded_value == Decimal("300000")


def test_empty_portfolio():
    r = run(cases=[], vals=[])
    assert r.borrowing_base == Decimal("0")
    assert r.available_credit == Decimal("0")


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        run(vals=VALS[:2])


def make_in(case_type, jurisdiction):
    return CaseInput(
        case_type=case_type,
        stage="discovery",
        filed_date=date(2024, 1, 1),
        projected_fee=Decimal("1"),
        jurisdiction=jurisdiction,
    )


PI_ONLY = {"pi": Decimal("0.5")}


def test_jurisdiction_cap_shrinks_over_cap_jurisdictions():
    cases = [make_in("pi", "NY"), make_in("pi", "NY"), make_in("pi", "TX"), make_in("pi", "TX")]
    r = run(
        limits={"per_jurisdiction": Decimal("0.25")},
        cases=cases,
        vals=[val("100000")] * 4,
        rates=PI_ONLY,
    )
    assert r.counted_value == Decimal("200000")
    assert r.borrowing_base == Decimal("100000")
    assert r.excluded_value == Decimal("200000")


def test_jurisdiction_cap_has_no_effect_when_under_the_cap():
    cases = [make_in("pi", "NY"), make_in("pi", "NY"), make_in("pi", "TX"), make_in("pi", "TX")]
    r = run(
        limits={"per_jurisdiction": Decimal("0.60")},
        cases=cases,
        vals=[val("100000")] * 4,
        rates=PI_ONLY,
    )
    assert r.counted_value == Decimal("400000")
    assert r.borrowing_base == Decimal("200000")


def test_single_case_cap_applies_before_jurisdiction_cap():
    r = run(
        limits={"single_case": Decimal("0.50"), "per_jurisdiction": Decimal("0.40")},
        cases=[make_in("pi", "NY"), make_in("pi", "TX")],
        vals=[val("300000"), val("100000")],
        rates=PI_ONLY,
    )
    # NY: 300k -> 200k (single-case cap) -> 160k (jurisdiction cap); TX stays 100k
    assert r.counted_value == Decimal("260000")
    assert r.borrowing_base == Decimal("130000")


def test_ineligible_cases_do_not_use_up_jurisdiction_room():
    r = run(
        limits={"per_jurisdiction": Decimal("0.30")},
        cases=[make_in("class_action", "NY"), make_in("pi", "NY"), make_in("pi", "TX")],
        vals=[val("300000"), val("100000"), val("100000")],
        rates=PI_ONLY,
    )
    assert r.counted_value == Decimal("200000")
    assert r.borrowing_base == Decimal("100000")
    assert r.excluded_value == Decimal("300000")
