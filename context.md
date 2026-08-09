# Argus — Project Context

Running state of the build. Read this first in any new session to get up to speed without re-explaining.

## Status: Phase 0 and Phase 1 complete. **Phase 2 (Demand Forecast Agent) complete and verified end-to-end** — XGBoost achieves 16.79% MAPE vs. 24.94% for a seasonal-naive baseline on the real dataset; 15,000 forecast rows (500 SKUs x 30-day horizon) written to Postgres. Starting Phase 3 (Anomaly/Risk Agent).

## What's built so far
- Directory structure: `backend/app/{agents,models,api,db,services}`, `backend/data/{raw,processed}`, `backend/notebooks`, `backend/tests`, `frontend/src/{components,pages,api}`, `docs/`.
- `docs/` now holds `PRD.md`, `SRS.md`, `design_architecture.md`, `techstack.md`, `style_guide.md` (moved from root to match `CLAUDE.md`'s declared repo structure). `CLAUDE.md` and `README.md` stay at root.
- `.gitignore`, `.env.example` in place.
- `backend/requirements.txt` — pinned deps (FastAPI, SQLAlchemy, psycopg2, pandas/numpy/xgboost/scikit-learn, langchain/langgraph/langchain-groq, pydantic-settings, pytest/ruff/black).
- `backend/app/config.py` — single `Settings` object (pydantic-settings) that every other file reads config through. No file outside `config.py` should call `os.getenv` directly.
- Git repo initialized locally (`git init -b main`) — no commits yet, user commits everything themselves.
- Kaggle Store Item Demand Forecasting dataset (`train.csv`, `test.csv`) downloaded and placed in `backend/data/raw/`.
- `backend/app/db/models.py` — SQLAlchemy 2.0 declarative models: `SalesRecord`, `Inventory`, `Forecast`, `RiskFlag`, `Recommendation`. No `Product`/`SKU` dimension table — `store_id`/`item_id` used directly everywhere, matching the dataset's natural grain (no extra product metadata exists to justify one).
- `config.py`/`.env.example` extended with inventory-synthesis tunables: `lead_time_days` (7), `inventory_lookback_days` (90), `inventory_days_of_cover_min/max` (3/21), `inventory_random_seed` (42). `config.py` also updated to Pydantic v2-native `model_config = SettingsConfigDict(...)` (was using the deprecated v1-style `class Config:`).
- `backend/app/db/session.py` — `engine`, `SessionLocal` factory, `get_db()` (FastAPI dependency, generator-based cleanup), `init_db()` (creates tables via `Base.metadata.create_all`, no Alembic — fixed schema, one-week batch project).
- `backend/pytest.ini`, `backend/tests/test_models.py`, `backend/tests/test_session.py` — 8 tests, all passing, run against in-memory SQLite (no live Postgres needed for these). Established as a per-file workflow rule going forward (see Working agreements).
- Python virtual environment created at `backend/argus-venv` (named per user preference, not the generic `venv`), with all of `requirements.txt` installed. `.gitignore` updated to exclude it.
- `docker-compose.yml` (project root) — minimal, Postgres-only for now (`argus-postgres` container, `argus_pgdata` named volume, port 5432). Backend/frontend services join this file in Phase 9, not before.
- **Real bug found and fixed**: `config.py`'s `env_file=".env"` resolved relative to the process's CWD, not the project root — running from `backend/` silently missed the real `.env` and fell back to hardcoded defaults with no error. Fixed by anchoring to `config.py`'s own file location: `_PROJECT_ROOT = Path(__file__).resolve().parents[2]`, then `env_file=_PROJECT_ROOT / ".env"`. Caught by manually testing from `backend/` with a distinctive `.env` value, confirmed via `backend/tests/test_config.py` (3 tests, including a CWD-change simulation).
- Verified end-to-end against the real Postgres container (not just SQLite unit tests): ran `init_db()` from `backend/`, confirmed all 5 tables exist via `psql \dt`. Full chain — compose → config → session → models — proven working together.
- `backend/app/services/data_ingestion.py` — `load_and_clean_sales()` (validate columns, coerce/drop bad dates, drop negative sales, drop duplicates), `load_sales_records()` and `synthesize_inventory()` (both delete-then-insert for idempotency, using `bulk_insert_mappings` for speed), `run_ingestion()` entrypoint, runnable directly via `python -m app.services.data_ingestion`.
  - **Second real bug found and fixed**: `psycopg2` can't adapt numpy scalar types (`numpy.int64`, etc.) that pandas produces — would have thrown `can't adapt type 'numpy.int64'` against real Postgres, but passed silently against SQLite in unit tests (SQLite's driver is more permissive). Added `_to_native_records()` to convert numpy scalars to native Python types before insert. Caught by deliberately validating against the real Postgres container instead of trusting SQLite-backed tests alone — same lesson as the `.env` bug, now a established habit for this project.
  - Ran against the full real dataset (not just test fixtures): 913,000 sales rows loaded, 500 inventory rows synthesized (10 stores × 50 items, as expected), spot-checked in Postgres directly.
  - `backend/tests/test_data_ingestion.py` — 7 tests covering cleaning edge cases (bad dates, negative sales, duplicates, missing columns) and DB logic (idempotency, one-row-per-SKU, seeded reproducibility) against in-memory SQLite.
- `backend/app/models/forecast_model.py` — `ForecastModel` (XGBoost wrapper, one global model across all 500 SKUs, not per-SKU models), `_add_calendar_features()` (year/month/day/day_of_week/day_of_year/week_of_year — no lag/rolling features in v1, documented simplicity call, see backlog "Known gaps"), `mean_absolute_percentage_error()`, `seasonal_naive_forecast()` (lag-7 baseline, looks up real historical values from the full sales history so no future information leaks in even when the lag lands inside the holdout window). Predictions clipped to >= 0 (demand can't be negative; XGBoost regression has no floor on its own).
- `backend/app/agents/forecast_agent.py` — `run(db) -> ForecastAgentOutput` (typed entrypoint per style_guide.md's agent convention). Temporal train/holdout split (not random shuffle — would leak future info), evaluates XGBoost vs. the seasonal-naive baseline, then retrains on the full dataset before writing the real forecast. Delete-then-insert into `forecasts`, same idempotency pattern as ingestion.
  - Forecast model hyperparameters (`forecast_n_estimators`=300, `forecast_max_depth`=6, `forecast_learning_rate`=0.05) added to `config.py`/`.env.example` — no hardcoded magic numbers, per `style_guide.md`.
  - **Real result on the full dataset**: XGBoost 16.79% MAPE vs. seasonal-naive 24.94% MAPE — ~33% relative error reduction. 15,000 forecast rows (500 SKUs x 30-day horizon) written and spot-checked directly in Postgres.
  - `backend/tests/test_forecast_model.py` (6 tests) + `backend/tests/test_forecast_agent.py` (3 tests, DB-integration style against in-memory SQLite with `monkeypatch`-shrunk horizon for speed) — 9 tests total, all passing alongside the real end-to-end Postgres run.

## Key decisions made and why
- **Frontend is plain JavaScript/JSX, not TypeScript.** `design_architecture.md`'s original diagram said "React + TypeScript" but `techstack.md` and `style_guide.md` both specify plain JS with no TS compiler. Fixed the diagram label to match; JS is the source of truth going forward.
- **Docs live under `docs/`.** They were originally all sitting at project root; moved to match `CLAUDE.md`'s own declared repo structure.
- **Postgres runs via Docker from day one**, not SQLite-first. User confirmed this up front since `docker-compose` is coming anyway per the build plan (Phase 9) and it matches `techstack.md`/SRS exactly.
- **Dataset acquired via manual download**, not the Kaggle API — one-time static pull, not worth the API token setup for a 2-3 day timeline.
- **`sample_submission.csv` was intentionally not kept** — it's Kaggle's submission-format template, unused by our pipeline.

## Deviations from the original 6 docs
- **Inventory levels are synthesized, not sourced.** The Kaggle Store Item Demand Forecasting dataset only has `date, store, item, sales` — no inventory field, despite `SRS.md` FR-3.1 and `design_architecture.md`'s Risk Agent both assuming "current inventory levels" as an input. Checked for alternative Kaggle datasets with real inventory data (e.g. `atomicd/retail-store-inventory-and-demand-forecasting`) — rejected, because those are themselves synthetic datasets with undocumented generation methods, and switching now would cost EDA time and require updating the dataset name across 4 docs for no real gain in "authenticity."
  - Synthesis approach (lives in the ingestion layer, not in agents, so agents stay generic per `CLAUDE.md`): per store-item, `avg_daily_demand` = mean sales over the trailing 90 days ending at the dataset's max date; `current_stock` = `avg_daily_demand × days_of_cover`, where `days_of_cover` is a seeded-random uniform value between 3 and 21 days (seed=42, reproducible across reruns). The random spread is intentional — it creates realistic variance so some SKUs land at-risk and others don't, instead of a flat/useless demo.
  - Generated once as a static snapshot (`as_of_date` = dataset's last date), not simulated day-by-day.
  - `LEAD_TIME_DAYS = 7` is a fixed config constant (not data-derived) used by both the Risk Agent (stockout check) and Inventory Agent (EOQ/reorder point calc later).
  - Both the lead time and the days-of-cover range are tunable via `config.py`/`.env`, not hardcoded — kept at defaults per user sign-off.
- TypeScript→JavaScript label fix in `design_architecture.md` diagram (doc inconsistency fix, not a scope deviation).

## Working agreements (see also CLAUDE.md)
- Claude never runs any `git` command, ever — always prints the command for the user to paste. This is broader than just "don't commit."
- Claude explains what a Bash command does and waits for explicit go-ahead before running it, even read-only commands.
- Commit messages use Conventional Commits prefixes (`feat:`, `fix:`, `docs:`, `chore:`, etc.) plus imperative-mood summary, per user preference (not originally specified in `style_guide.md`).
- User already knows Pydantic and `.env`-based config — no need to re-explain those from scratch.
- **Write and run tests for each file immediately after building it, before starting the next file** — added to `CLAUDE.md` Ground Rules. Catch breakage early, not several files later.
- **Update `README.md`, `context.md`, `backlog.md` before every commit, not after** — added to `CLAUDE.md` Ground Rules. The user checks these are current as part of their decision to commit.

## Next up
- Phase 3: Anomaly/Risk Agent (`backend/app/agents/risk_agent.py`) — reads `forecasts` + `inventory`, applies the stockout threshold (`stockout_risk_threshold`, `lead_time_days`) and a z-score anomaly check (`anomaly_zscore_threshold`), writes `risk_flags`.

## Local dev notes
- Postgres runs via `docker compose up -d` (project root). Check status: `docker compose ps`. Real `.env` (git-ignored) must exist at the project root — copy from `.env.example` if missing.
- To (re)populate the database from the CSV: `cd backend && argus-venv/bin/python -m app.services.data_ingestion` (idempotent — safe to re-run).
- To (re)generate forecasts: `cd backend && argus-venv/bin/python -m app.agents.forecast_agent` (idempotent — safe to re-run; requires `sales_records` to be populated first).
