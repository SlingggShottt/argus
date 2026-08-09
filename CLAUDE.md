# CLAUDE.md — Project: Argus

This file orients Claude (or any AI coding assistant) working in this repo. Read this before making changes.

## What Argus Is
Argus is an agentic decision-intelligence platform for supply chain demand forecasting, risk detection, and inventory optimization. It ingests sales/inventory data, forecasts demand, flags stockout/anomaly risk, recommends reorder actions, and answers natural-language business questions via an LLM agent.

Built as a portfolio project for an AI-Analyst role — prioritize working, demoable code over exhaustive polish. One week timeline.

## Repo Structure

argus/
├── backend/
│ ├── app/
│ │ ├── agents/ # LangChain/LangGraph agent definitions
│ │ ├── models/ # ML models (forecast, anomaly detection)
│ │ ├── api/ # FastAPI routes
│ │ ├── db/ # SQLAlchemy models, migrations
│ │ ├── services/ # business logic
│ │ └── main.py
│ ├── data/ # raw + processed dataset
│ ├── notebooks/ # EDA and model prototyping
│ ├── tests/
│ └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/               
│   │   └── App.jsx
│   └── package.json
├── docker-compose.yml
├── docs/
│ ├── SRS.md
│ ├── PRD.md
│ ├── design_architecture.md
│ ├── techstack.md
│ └── style_guide.md
└── README.md

## Ground Rules
- Follow `docs/style_guide.md` for all code style and naming.
- Follow `docs/design_architecture.md` before changing agent orchestration or data flow — don't improvise a different architecture mid-build.
- Prefer fully automated, copy-paste-ready scripts over manual steps (setup scripts, seed scripts, one-command Docker startup).
- Keep the LLM layer swappable — call it through a single `llm_client.py` wrapper, not scattered API calls, so switching Groq → Ollama later is a one-file change.
- No secrets committed. All keys via `.env`, with `.env.example` kept up to date.
- Write code and comments in plain, direct language. No filler docstrings, no restating the obvious.
- **Test after every file, not at the end.** As soon as a file/unit is built, write and run tests for it before moving to the next file. Catches failures immediately instead of discovering them after several more files are built on top of a broken one.
- **Update `README.md`, `context.md`, and `backlog.md` before every commit** — not after. The user reviews these updates as part of deciding whether to commit, so they must be current *before* a commit message is proposed, every time, no exceptions.

## Commands (fill in once scaffolded)
```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Full stack
docker-compose up --build

# Tests
cd backend && pytest
```

## Current Build Priority (in order)
1. Data ingestion + cleaning (Kaggle Store Item Demand Forecasting)
2. Demand Forecast Agent
3. Anomaly/Risk Agent
4. Inventory Optimization Agent
5. LangGraph orchestrator tying agents together
6. Conversational Insight Agent (Groq-backed)
7. FastAPI endpoints exposing all of the above
8. React dashboard (KPIs, alerts, chat)
9. Docker Compose for local run
10. Render deployment (free tier — changed from the original AWS plan, see context.md)

## What NOT to do
- Don't add authentication/multi-tenancy — out of scope, wastes build time.
- Don't over-engineer the ML models — a solid, explainable baseline (XGBoost/Prophet) beats a marginally-better black-box model for interview purposes.
- Don't hardcode dataset-specific logic deep in agents — keep agents generic enough to explain "this generalizes to other SKUs/datasets" in an interview.