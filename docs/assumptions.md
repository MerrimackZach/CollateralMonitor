# Model Assumptions

All values are **illustrative** and chosen for a portfolio project built on synthetic
data. They are not drawn from any real firm, lender, or case outcomes.

## Stages

Cases in the collateral pool are in one of three active stages:
`filed`, `discovery`, `settlement_talks`. Resolved cases are not collateral.

## Probability of recovery (win or settlement)

| Case type    | filed | discovery | settlement_talks |
|--------------|-------|-----------|------------------|
| mass_tort    | 0.55  | 0.65      | 0.80             |
| class_action | 0.45  | 0.60      | 0.75             |
| pi           | 0.65  | 0.75      | 0.88             |

## Expected years until resolution

| Case type    | filed | discovery | settlement_talks |
|--------------|-------|-----------|------------------|
| mass_tort    | 5.0   | 3.5       | 1.5              |
| class_action | 4.0   | 2.5       | 1.0              |
| pi           | 2.0   | 1.2       | 0.5              |

## Valuation

- expected fee = probability of recovery x projected fee
- present value = expected fee / (1 + discount rate) ^ years
- discount rate: 12% per year

## Projected fee ranges per case (USD)

| Case type    | Low     | High       |
|--------------|---------|------------|
| mass_tort    | 10,000  | 80,000     |
| class_action | 500,000 | 15,000,000 |
| pi           | 15,000  | 400,000    |

## Lending terms (defaults)

| Case type    | Advance rate |
|--------------|--------------|
| mass_tort    | 0.30         |
| class_action | 0.35         |
| pi           | 0.45         |

- Concentration limit: no single case type may exceed 60% of the borrowing base
- Minimum collateral coverage ratio: 1.50

## Additional rules and notes

- Single-case concentration limit: no single case may exceed 10% of the borrowing base
- Coverage ratio = present value of eligible collateral / outstanding balance
- Fee units differ by type: a mass_tort or pi case is one claimant matter; a class_action
  case is an entire matter. Synthetic portfolios therefore contain many mass_tort and pi
  cases and only a few class actions.
- Probabilities and durations are point estimates in the valuation engine. The Monte Carlo
  phase will sample around them.

## Borrowing base rules

1. Each case counts at its present value.
2. Single-case cap: a case counts for at most 10% of total present value; the excess is excluded.
3. Case-type cap: a case type counts for at most 60% of total present value, after step 2.
4. Both caps are measured against total present value before any exclusions (a simplification).
5. A case type with no advance rate is ineligible and counts for nothing.
6. Borrowing base = sum over case types of (counted value x advance rate).
7. Available credit = max(0, min(borrowing base, commitment) - outstanding balance).
