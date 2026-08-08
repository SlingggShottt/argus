# Argus — Project Context

Running state of the build. Read this first in any new session to get up to speed without re-explaining.

## Status: Phase 0 (scaffolding) — in progress

## What's built so far
- Directory structure: `backend/app/{agents,models,api,db,services}`, `backend/data/{raw,processed}`, `backend/notebooks`, `backend/tests`, `frontend/src/{components,pages,api}`, `docs/`.
- `docs/` now holds `PRD.md`, `SRS.md`, `design_architecture.md`, `techstack.md`, `style_guide.md` (moved from root to match `CLAUDE.md`'s declared repo structure). `CLAUDE.md` and `README.md` stay at root.
- `.gitignore`, `.env.example` in place.
- `backend/requirements.txt` — pinned deps (FastAPI, SQLAlchemy, psycopg2, pandas/numpy/xgboost/scikit-learn, langchain/langgraph/langchain-groq, pydantic-settings, pytest/ruff/black).
- `backend/app/config.py` — single `Settings` object (pydantic-settings) that every other file reads config through. No file outside `config.py` should call `os.getenv` directly.
- Git repo initialized locally (`git init -b main`) — no commits yet, user commits everything themselves.
- Kaggle Store Item Demand Forecasting dataset (`train.csv`, `test.csv`) downloaded and placed in `backend/data/raw/`.

## Key decisions made and why
- **Frontend is plain JavaScript/JSX, not TypeScript.** `design_architecture.md`'s original diagram said "React + TypeScript" but `techstack.md` and `style_guide.md` both specify plain JS with no TS compiler. Fixed the diagram label to match; JS is the source of truth going forward.
- **Docs live under `docs/`.** They were originally all sitting at project root; moved to match `CLAUDE.md`'s own declared repo structure.
- **Postgres runs via Docker from day one**, not SQLite-first. User confirmed this up front since `docker-compose` is coming anyway per the build plan (Phase 9) and it matches `techstack.md`/SRS exactly.
- **Dataset acquired via manual download**, not the Kaggle API — one-time static pull, not worth the API token setup for a 2-3 day timeline.
- **`sample_submission.csv` was intentionally not kept** — it's Kaggle's submission-format template, unused by our pipeline.

## Deviations from the original 6 docs
- None yet beyond the TypeScript→JavaScript label fix above (that was a doc inconsistency fix, not a scope deviation).

## Working agreements (see also CLAUDE.md)
- Claude never runs any `git` command, ever — always prints the command for the user to paste. This is broader than just "don't commit."
- Claude explains what a Bash command does and waits for explicit go-ahead before running it, even read-only commands.
- Commit messages use Conventional Commits prefixes (`feat:`, `fix:`, `docs:`, `chore:`, etc.) plus imperative-mood summary, per user preference (not originally specified in `style_guide.md`).
- User already knows Pydantic and `.env`-based config — no need to re-explain those from scratch.

## Next up
- Finish Phase 0: `backlog.md` (this session).
- Phase 1: data ingestion — SQLAlchemy models, DB session setup, cleaning/loading script for `train.csv` into Postgres.
