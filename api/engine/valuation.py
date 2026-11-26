from dataclasses import dataclass
from decimal import Decimal

from engine.inputs import CaseInput
from engine.transition import TransitionModel

CENTS = Decimal("0.01")
DEFAULT_DISCOUNT_RATE = Decimal("0.12")  # per year, illustrative


@dataclass(frozen=True)
class CaseValuation:
    expected_fee: Decimal
    present_value: Decimal


@dataclass(frozen=True)
class PortfolioValuation:
    case_valuations: list[CaseValuation]  # same order as the input cases
    total_expected_fee: Decimal
    total_present_value: Decimal


def value_case(
    case: CaseInput,
    model: TransitionModel,
    discount_rate: Decimal = DEFAULT_DISCOUNT_RATE,
) -> CaseValuation:
    """expected fee = probability x projected fee
    present value = expected fee / (1 + discount rate) ^ years remaining
    """
    outlook = model.outlook(case)
    expected_fee = case.projected_fee * outlook.probability
    discount_factor = (Decimal(1) + discount_rate) ** outlook.years_remaining
    present_value = expected_fee / discount_factor
    return CaseValuation(
        expected_fee=expected_fee.quantize(CENTS),
        present_value=present_value.quantize(CENTS),
    )


def value_portfolio(
    cases: list[CaseInput],
    model: TransitionModel,
    discount_rate: Decimal = DEFAULT_DISCOUNT_RATE,
) -> PortfolioValuation:
    valuations = [value_case(c, model, discount_rate) for c in cases]
    return PortfolioValuation(
        case_valuations=valuations,
        total_expected_fee=sum((v.expected_fee for v in valuations), Decimal("0")),
        total_present_value=sum((v.present_value for v in valuations), Decimal("0")),
    )
