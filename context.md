# Argus — Project Context

Running state of the build. Read this first in any new session to get up to speed without re-explaining.

## Status: Phase 0 complete and committed. Phase 1 (data ingestion) in progress — DB schema defined, ingestion script not yet written.

## What's built so far
- Directory structure: `backend/app/{agents,models,api,db,services}`, `backend/data/{raw,processed}`, `backend/notebooks`, `backend/tests`, `frontend/src/{components,pages,api}`, `docs/`.
- `docs/` now holds `PRD.md`, `SRS.md`, `design_architecture.md`, `techstack.md`, `style_guide.md` (moved from root to match `CLAUDE.md`'s declared repo structure). `CLAUDE.md` and `README.md` stay at root.
- `.gitignore`, `.env.example` in place.
- `backend/requirements.txt` — pinned deps (FastAPI, SQLAlchemy, psycopg2, pandas/numpy/xgboost/scikit-learn, langchain/langgraph/langchain-groq, pydantic-settings, pytest/ruff/black).
- `backend/app/config.py` — single `Settings` object (pydantic-settings) that every other file reads config through. No file outside `config.py` should call `os.getenv` directly.
- Git repo initialized locally (`git init -b main`) — no commits yet, user commits everything themselves.
- Kaggle Store Item Demand Forecasting dataset (`train.csv`, `test.csv`) downloaded and placed in `backend/data/raw/`.
- `backend/app/db/models.py` — SQLAlchemy 2.0 declarative models: `SalesRecord`, `Inventory`, `Forecast`, `RiskFlag`, `Recommendation`. No `Product`/`SKU` dimension table — `store_id`/`item_id` used directly everywhere, matching the dataset's natural grain (no extra product metadata exists to justify one).
- `config.py`/`.env.example` extended with inventory-synthesis tunables: `lead_time_days` (7), `inventory_lookback_days` (90), `inventory_days_of_cover_min/max` (3/21), `inventory_random_seed` (42).

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

## Next up
- Phase 1: `backend/app/db/session.py` (engine/session setup), then the cleaning/loading + inventory-synthesis script for `train.csv` into Postgres.
