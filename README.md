# Argus

Agentic decision-intelligence platform for supply chain demand forecasting and inventory risk management. Enterprises with large product catalogs struggle to quickly answer questions like "which SKUs are about to stock out?" or "what should we reorder, and when?" — Argus ingests historical sales/inventory data, forecasts demand, flags stockout/anomaly risk, recommends reorder actions, and answers natural-language questions about all of it via an LLM agent grounded in that structured output.

Built as a portfolio project for an AI-Analyst role.

## Status

**Phase 0 and Phase 1 (data ingestion) complete.** The database is live and populated: 913,000 real sales rows plus a synthesized inventory snapshot (500 store-item rows) in Postgres via Docker Compose, all verified end-to-end (not just unit tests). No runnable API/frontend yet — that starts with the Forecast Agent in Phase 2. Note: the dataset has no real inventory data, so inventory levels are synthesized at ingestion time from trailing sales averages — see `context.md` for the exact formula and assumptions. This section will be updated as each phase lands; see `context.md` for a detailed running log and `backlog.md` for what's left.

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

# Create the database tables, then load and clean the dataset
# (idempotent — safe to re-run; also synthesizes the inventory snapshot)
cd backend
argus-venv/bin/python -c "from app.db.session import init_db; init_db()"
argus-venv/bin/python -m app.services.data_ingestion
```

Dataset: the Kaggle [Store Item Demand Forecasting](https://www.kaggle.com/c/demand-forecasting-kernels-only/data) `train.csv` and `test.csv` are expected in `backend/data/raw/` (not committed — see `.gitignore`).

Run backend tests (DB/schema tests run against in-memory SQLite, no Postgres required):
```bash
cd backend && argus-venv/bin/pytest -v
```

The full Docker Compose stack (backend/frontend containers) and the frontend dev server are not wired up yet (Phases 8-9 of the build plan in `CLAUDE.md`).

## Results

Not yet available — forecast accuracy (MAPE vs. a naive baseline) and a demo walkthrough will be added here once the Forecast Agent and dashboard are built.

## Project docs

- `docs/PRD.md` — product requirements
- `docs/SRS.md` — functional/non-functional requirements
- `docs/design_architecture.md` — architecture detail and design rationale
- `docs/techstack.md` — tech choices and why
- `docs/style_guide.md` — code style and conventions
- `context.md` — running build log (read this for full current state)
- `backlog.md` — pending work and known gaps
