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