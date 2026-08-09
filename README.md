# Argus

Agentic decision-intelligence platform for supply chain demand forecasting and inventory risk management. Enterprises with large product catalogs struggle to quickly answer questions like "which SKUs are about to stock out?" or "what should we reorder, and when?" — Argus ingests historical sales/inventory data, forecasts demand, flags stockout/anomaly risk, recommends reorder actions, and answers natural-language questions about all of it via an LLM agent grounded in that structured output.

Built as a portfolio project for an AI-Analyst role.

## Status

**Phases 0-5 complete.** The three deterministic agents (Forecast, Risk, Inventory) now run as one LangGraph pipeline, verified end-to-end against Postgres with results identical to running each agent individually. No runnable API/frontend yet — next up is the Groq-backed Conversational Agent (Phase 6), then FastAPI endpoints (Phase 7) and the dashboard (Phase 8). Note: the dataset has no real inventory or cost data, so inventory levels and EOQ cost inputs are documented, config-tunable assumptions — see `context.md` for the exact formulas. This section will be updated as each phase lands; see `context.md` for a detailed running log and `backlog.md` for what's left.

## Architecture

```
                     ┌────────────────────┐
                     │      Frontend       │
                     │  React (JavaScript) │
                     │  (Dashboard + Chat)  │
                     └──────────┬───────────┘
                                │ REST (HTTPS)
                     ┌──────────▼───────────┐
                     │      FastAPI          │
                     │   (API Gateway Layer) │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │     Orchestrator       │
                     │  (LangGraph controller)│
                     └───┬────────┬─────┬────┘
                         │        │     │
             ┌───────────▼─┐ ┌────▼───┐ ┌▼────────────┐
             │ Forecast     │ │ Risk /  │ │ Inventory   │
             │ Agent        │ │ Anomaly │ │ Optimization│
             │ (XGBoost/    │ │ Agent   │ │ Agent       │
             │  Prophet)    │ │         │ │ (EOQ calc)  │
             └───────┬──────┘ └────┬────┘ └──────┬──────┘
                     │             │              │
                     └─────────────┼──────────────┘
                                   │  combined output
                     ┌─────────────▼──────────────┐
                     │ Conversational Insight Agent │
                     │  (Groq-hosted Llama/Mixtral,  │
                     │   grounded in agent outputs)  │
                     └─────────────┬──────────────┘
                                   │
                     ┌─────────────▼──────────────┐
                     │        PostgreSQL            │
                     │ (raw data, forecasts, logs)  │
                     └───────────────────────────────┘
```

Deterministic agents (Forecast, Risk, Inventory) run first and produce structured data; the LLM-backed Conversational Agent runs last and only reasons over that structured output — not raw data — to keep answers grounded. See `docs/design_architecture.md` for the full breakdown.

## Tech Stack

Python 3.11+ / FastAPI / LangGraph / XGBoost / PostgreSQL on the backend, React (JavaScript, Vite, Tailwind, Recharts) on the frontend, Groq-hosted open-source LLM for the conversational layer, Docker Compose for local orchestration. Full rationale in `docs/techstack.md`.

## Setup

Not yet runnable end-to-end — this section covers what's usable today and will grow as each phase lands.

```bash
# Clone and enter the repo
git clone <repo-url>
cd argus

# Backend: create a virtual environment and install dependencies
cd backend
python3 -m venv argus-venv
source argus-venv/bin/activate
pip install -r requirements.txt

# Copy the environment template and fill in real values
cd ..
cp .env.example .env
# edit .env: set DATABASE_URL, GROQ_API_KEY, etc.

# Start Postgres (Docker Compose is Postgres-only for now — full stack is Phase 9)
docker compose up -d

# Create the database tables and load the dataset, then run the full
# deterministic pipeline in one shot via the orchestrator (idempotent)
cd backend
argus-venv/bin/python -c "from app.db.session import init_db; init_db()"
argus-venv/bin/python -m app.services.data_ingestion
argus-venv/bin/python -m app.agents.orchestrator
```

Dataset: the Kaggle [Store Item Demand Forecasting](https://www.kaggle.com/c/demand-forecasting-kernels-only/data) `train.csv` and `test.csv` are expected in `backend/data/raw/` (not committed — see `.gitignore`).

Run backend tests (DB/schema tests run against in-memory SQLite, no Postgres required):
```bash
cd backend && argus-venv/bin/pytest -v
```

The full Docker Compose stack (backend/frontend containers) and the frontend dev server are not wired up yet (Phases 8-9 of the build plan in `CLAUDE.md`).

## Results

**Demand forecast (XGBoost, global model across all 500 store-item combinations)**: 16.79% MAPE on a held-out 30-day window, vs. 24.94% MAPE for a seasonal-naive baseline (predicting each day from the same SKU's actual sales 7 days earlier) — roughly a third lower error than a reasonable, non-trivial baseline. Evaluated on a strict temporal holdout (trained only on data before the held-out window, never a random shuffle-split, which would leak future information). See `context.md` for the full methodology.

**Risk detection**: 87 of 500 SKUs flagged for stockout risk (55 high severity — will run out before a reorder could arrive; 32 medium — dangerously close), driven by the synthesized inventory's cover range against a 7-day lead time. 0 SKUs flagged as demand anomalies for the most recent week — independently verified as a genuine result (max z-score 1.61 against a 2.5 threshold, computed via a standalone diagnostic), not a silent detection failure.

**Inventory recommendations**: reorder point and EOQ-based reorder quantity computed for all 500 SKUs via standard safety-stock and EOQ formulas (see `context.md` for the exact formulas and the documented cost-input assumptions, since the dataset has no real price data).

A demo walkthrough (screenshots/GIF) will be added once the dashboard is built.

## Project docs

- `docs/PRD.md` — product requirements
- `docs/SRS.md` — functional/non-functional requirements
- `docs/design_architecture.md` — architecture detail and design rationale
- `docs/techstack.md` — tech choices and why
- `docs/style_guide.md` — code style and conventions
- `context.md` — running build log (read this for full current state)
- `backlog.md` — pending work and known gaps
