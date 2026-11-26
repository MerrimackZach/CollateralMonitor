"""Print borrowing base and covenant status for every seeded firm."""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Firm
from app.services import load_case_inputs, load_facility_terms
from engine.borrowing_base import compute_borrowing_base
from engine.covenants import check_covenants
from engine.transition import LookupTransitionModel
from engine.valuation import value_portfolio


def main() -> None:
    model = LookupTransitionModel()
    with SessionLocal() as session:
        names = session.scalars(select(Firm.name).order_by(Firm.name)).all()
        for name in names:
            cases = load_case_inputs(session, name)
            terms = load_facility_terms(session, name)
            valuation = value_portfolio(cases, model)
            base = compute_borrowing_base(
                cases,
                valuation.case_valuations,
                advance_rates=terms.advance_rates,
                concentration_limits=terms.concentration_limits,
                commitment=terms.commitment,
                outstanding=terms.outstanding,
            )
            cov = check_covenants(
                base,
                outstanding=terms.outstanding,
                min_coverage_ratio=terms.min_coverage_ratio,
            )

            print(name)
            print(f"  present value:    ${base.total_present_value:>14,.0f}")
            print(f"  counted value:    ${base.counted_value:>14,.0f}")
            print(f"  excluded value:   ${base.excluded_value:>14,.0f}")
            print(f"  borrowing base:   ${base.borrowing_base:>14,.0f}")
            print(f"  commitment:       ${terms.commitment:>14,.0f}")
            print(f"  outstanding:      ${terms.outstanding:>14,.0f}")
            print(f"  available credit: ${base.available_credit:>14,.0f}")
            ratio = "n/a" if cov.coverage_ratio is None else f"{cov.coverage_ratio}x"
            status = "BREACH" if cov.coverage_breached else "ok"
            print(f"  coverage ratio:   {ratio} (minimum {cov.min_coverage_ratio}x) {status}")
            print(f"  base deficiency:  ${cov.borrowing_base_deficiency:>14,.0f}")
            for case_type, t in sorted(base.by_type.items()):
                print(
                    f"    {case_type}: counted ${t.counted_value:,.0f}, "
                    f"base ${t.borrowing_base:,.0f}"
                )


if __name__ == "__main__":
    main()
