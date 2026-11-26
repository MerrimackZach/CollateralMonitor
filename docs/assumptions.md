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
