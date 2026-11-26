"""Print a valuation summary for every seeded firm."""
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Firm
from app.services import load_case_inputs
from engine.transition import LookupTransitionModel
from engine.valuation import value_portfolio


def main() -> None:
    model = LookupTransitionModel()
    with SessionLocal() as session:
        names = session.scalars(select(Firm.name).order_by(Firm.name)).all()
        for name in names:
            cases = load_case_inputs(session, name)
            result = value_portfolio(cases, model)
            projected = sum((c.projected_fee for c in cases), Decimal("0"))

            print(name)
            print(f"  projected fees: ${projected:>14,.0f}")
            print(f"  expected fees:  ${result.total_expected_fee:>14,.0f}")
            print(f"  present value:  ${result.total_present_value:>14,.0f}")

            by_type = defaultdict(Decimal)
            for case, val in zip(cases, result.case_valuations):
                by_type[case.case_type] += val.present_value
            for case_type, pv in sorted(by_type.items()):
                print(f"    {case_type}: ${pv:,.0f}")


if __name__ == "__main__":
    main()
