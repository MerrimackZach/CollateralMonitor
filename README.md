# CollateralMonitor
Litigation portfolio collateral monitoring and valuation platform. This is built on synthetic data. 
## Build Log

### Day 1: Project setup

**Goal:** Stand up the project foundation for a litigation portfolio collateral monitor (valuation, borrowing base, and covenant tracking on synthetic data).

**Done**
- Created the GitHub repo with an MIT license and Python `.gitignore`
- Set up the project structure: `api/` (app, engine, migrations, tests), `web/`, `data/`, `docs/`
- Added Docker Compose to run PostgreSQL 16 locally
- Created a Python virtual environment with FastAPI, SQLAlchemy, Alembic, pandas, NumPy, pytest, and ruff

**Design decisions**
- Financial logic lives in `api/engine/`, separate from the web layer, so it can be tested on its own
- Lending rules (advance rates, concentration limits) will be stored in database tables instead of hard-coded
- Stage-transition logic will sit behind an interface so a more refined model can be swapped in later

**Concepts covered**
- Contingency-fee cases as collateral, advance rates, borrowing base, concentration limits, covenants

**Next:** Phase 1, SQLAlchemy models and the first Alembic migration.
----------------------------------------------------


### Day 2: Data model, valuation engine, borrowing base, and covenants

**Goal:** Build the core of the platform: database schema, synthetic data, valuation, borrowing base, and covenant checks (Phases 1-3).

**Done**
- **Data model:** 6 SQLAlchemy models (firms, facilities, cases, advance rates, concentration limits, valuations) with 2 Alembic migrations. Money is stored as exact decimals, not floats.
- **Synthetic data:** a seeded generator and an idempotent seed script that load 3 demo firms (about 700 cases total) with different sizes and risk profiles. All data is synthetic and the assumptions are documented in `docs/assumptions.md`.
- **Valuation engine:** expected fee and present value per case, using stage probabilities, time to resolution, and a 12% discount rate. Stage logic sits behind a `TransitionModel` interface so a more refined model can be swapped in later.
- **Borrowing base:** advance rates by case type, with single-case (10%), case-type (60%), and per-jurisdiction (25%) concentration caps applied in a defined order. Available credit is capped by the facility commitment.
- **Covenants:** minimum collateral coverage ratio (1.50x) and a borrowing base deficiency check.
- **Database-to-engine loader and report script:** run the whole pipeline on the seeded firms and print results.

**Testing:** 26 unit tests, all passing (`python -m pytest` from `api/`). They include a hand-checked valuation example, concentration cap edge cases, cap ordering, ineligible case types, empty portfolios, and covenant boundary conditions.

**Results (synthetic portfolios)**

| Firm | Present value | Borrowing base | Available credit | Coverage |
|---|---|---|---|---|
| Alpha | $7.40M | $1.72M | $225k | 2.99x |
| Bravo | $10.38M | $2.86M | $0 | 2.67x |
| Charlie | $31.85M | $11.50M | $3.50M | 3.64x |

**Findings**
- Bravo passes the 1.5x coverage covenant but is **$139k over-advanced** against its borrowing base. The two tests catch different risks, so the model tracks both.
- Alpha's three class actions all hit the single-case cap, which excluded 38% of its present value before the jurisdiction cap trimmed it further. A few large cases can dominate a portfolio that looks diversified by case count.
- Charlie, the most diversified firm, had the smallest share of value excluded (9%).

**Design decisions**
- Financial logic lives in `api/engine/` with no database or web dependencies, so it can be tested in isolation.
- Lending rules (advance rates, concentration limits) are stored in tables instead of hard-coded.
- Ineligible case types are removed before caps apply, so they can't use up another cap's room.

**Next:** Phase 4, Monte Carlo simulation, to estimate how often collateral falls short of the outstanding balance.

---

### Day 3: Monte Carlo simulation (Phase 4)

**Goal:** Estimate the range of possible portfolio values, not just one expected value, and measure how often collateral would fall short of what is owed.

**Done**
- **Single-case simulator:** each scenario rolls win or loss for a case, draws a random resolution time (lognormal, centered on the Phase 2 expected time), and discounts the fee at 12%.
- **Portfolio simulation:** sums every case's value within each scenario, then reports the mean, P10, P50, P90, and the shortfall probability (share of scenarios where value falls below the outstanding balance). One seeded random generator makes every run reproducible.
- **Adapter:** converts engine case inputs into simulation inputs through any `TransitionModel`, so the stretch-phase model will plug in unchanged. This is also the one place `Decimal` money becomes `float`.
- **Shared shock (correlation):** cases of the same type share one random factor per scenario (a one-factor Gaussian copula), so mass torts tend to win or lose together. Each case keeps its own win probability, so averages barely move while the spread widens. PI cases stay independent.
- **Report script:** runs every seeded firm under three settings: independent, moderate (mass tort 0.30, class action 0.20), and high (mass tort 0.60, class action 0.40).

**Testing:** 41 tests, all passing (15 new, 26 from Phases 1-3). They include a check against theory (two fair-coin cases at correlation 0.9 should both win about 43% of the time), identical results from identical seeds, and a cross-check of the simulated mean against the hand-checked Phase 2 valuation.

**Results (synthetic portfolios, 10,000 scenarios, seed 42, $M)**

| Firm | Phase 2 value | Outstanding |
|---|---|---|
| Alpha | 7.40 | 1.50 |
| Bravo | 10.38 | 3.00 |
| Charlie | 31.85 | 8.00 |

| Firm | Correlation | Mean | P10 | P50 | P90 | Shortfall |
|---|---|---|---|---|---|---|
| Alpha | independent | 7.44 | 3.83 | 7.32 | 10.77 | 0.00% |
| Alpha | moderate | 7.46 | 3.57 | 7.38 | 10.88 | 0.02% |
| Alpha | high | 7.45 | 2.94 | 7.46 | 10.96 | 0.05% |
| Bravo | independent | 10.46 | 5.96 | 10.98 | 14.62 | 0.00% |
| Bravo | moderate | 10.53 | 5.81 | 10.86 | 15.03 | 0.25% |
| Bravo | high | 10.54 | 5.43 | 10.90 | 15.52 | 1.86% |
| Charlie | independent | 32.06 | 23.25 | 32.01 | 40.08 | 0.00% |
| Charlie | moderate | 32.02 | 21.64 | 32.30 | 41.35 | 0.00% |
| Charlie | high | 32.04 | 19.89 | 32.63 | 42.27 | 0.00% |

Nine simulations of 10,000 scenarios (90,000 total) ran in 0.60 seconds, including database loads.

**Findings**
- Simulated means stay within about 1.5% of the Phase 2 values in every run. They sit slightly above because random timelines are discounted one by one, and averaging those discounts gives a bit more than discounting the average timeline.
- Correlation changes the spread, not the average. Going from independent to high, P10 falls 23% for Alpha, 9% for Bravo, and 14% for Charlie, while P90 rises.
- Case count is a poor measure of diversification. Class actions are 68% of Alpha's present value, 43% of Bravo's (from just 2 cases), and 50% of Charlie's (spread over 8 cases). Bravo has about 290 cases, yet its spread is nearly as wide as Alpha's.
- Only Bravo shows a meaningful shortfall: 0.25% at moderate correlation and 1.86% at high. It combines a high balance relative to its collateral with a wide spread. Charlie borrows a similar share but has the tightest spread, so it never falls short.

**Design decisions**
- Simulation code lives in `api/engine/` with no database or web dependencies, like the rest of the engine.
- Correlation is set per case type and applied as a shared factor, so each case's win probability is preserved exactly.
- Correlation values are illustrative assumptions, not estimated from data.

**Limitations**
- Fees are fixed at each case's projected fee; only win/loss and timing are random.
- Shortfall compares raw simulated value to the balance. The real covenant uses value counted after concentration caps.

**Next:** covenant breach probability (how often coverage falls below 1.5x under simulation), then Phase 5, the API.