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