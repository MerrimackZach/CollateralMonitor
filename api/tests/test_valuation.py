from datetime import date
from decimal import Decimal

import pytest

from engine.inputs import CaseInput
from engine.transition import LookupTransitionModel
from engine.valuation import value_case, value_portfolio

model = LookupTransitionModel()


def make_case(case_type="mass_tort", stage="discovery", fee="40000"):
    return CaseInput(
        case_type=case_type,
        stage=stage,
        filed_date=date(2024, 1, 1),
        projected_fee=Decimal(fee),
        jurisdiction="NY",
    )


def test_hand_checked_example():
    v = value_case(make_case(), model)
    assert v.expected_fee == Decimal("26000.00")
    assert float(v.present_value) == pytest.approx(17486.80, abs=0.1)


def test_present_value_below_expected_fee_below_projected_fee():
    case = make_case()
    v = value_case(case, model)
    assert v.present_value < v.expected_fee < case.projected_fee


def test_later_stage_is_worth_more():
    early = value_case(make_case(stage="filed"), model)
    late = value_case(make_case(stage="settlement_talks"), model)
    assert late.present_value > early.present_value


def test_zero_discount_rate_gives_expected_fee():
    v = value_case(make_case(), model, discount_rate=Decimal("0"))
    assert v.present_value == v.expected_fee


def test_portfolio_totals_match_cases():
    cases = [make_case(), make_case(case_type="pi", stage="filed", fee="100000")]
    result = value_portfolio(cases, model)
    assert len(result.case_valuations) == 2
    assert result.total_present_value == sum(
        v.present_value for v in result.case_valuations
    )


def test_empty_portfolio_is_zero():
    result = value_portfolio([], model)
    assert result.total_present_value == Decimal("0")


def test_unknown_stage_raises():
    with pytest.raises(ValueError):
        value_case(make_case(stage="appeal"), model)
