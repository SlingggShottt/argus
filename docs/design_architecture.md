# Design & Architecture — Argus

## 1. High-Level Architecture

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

## 2. Component Responsibilities

### Frontend (React)
- Dashboard: forecast charts (per SKU/store), risk/alert list, reorder recommendation table.
- Chat panel: sends NL queries to `/api/query`, renders grounded answers.
- Talks only to FastAPI — no direct DB or agent access.

### FastAPI (API Gateway)
- Thin layer: validates requests, calls orchestrator or specific agents, returns JSON.
- Exposes OpenAPI docs automatically (useful to show in interview — "here's the contract").
- Endpoints (indicative):
  - `GET /api/forecast/{store_id}/{item_id}`
  - `GET /api/risks`
  - `GET /api/recommendations`
  - `POST /api/query` (NL question → grounded answer)

### Orchestrator (LangGraph)
- Defines the agent execution graph: Forecast → Risk → Inventory → (combined context) → Conversational Agent.
- Deterministic agents (Forecast, Risk, Inventory) run first and produce structured data.
- Conversational agent is the only LLM-backed node in the core pipeline — it consumes structured outputs rather than raw data, which keeps answers grounded and reduces hallucination risk.
- Logs intermediate outputs at each node for explainability (NFR-2).

### Forecast Agent
- Input: historical sales data per store-item.
- Model: start with a solid baseline (XGBoost or Prophet); document accuracy vs a naive baseline.
- Output: forecast for a configurable horizon, plus confidence bounds if using Prophet.

### Risk/Anomaly Agent
- Input: forecast output + current inventory levels.
- Logic: rule-based thresholds (e.g., projected demand > available stock within lead time = stockout risk) plus a simple statistical anomaly check (e.g., z-score on demand deviation).
- Output: list of flagged SKUs with risk type and severity.

### Inventory Optimization Agent
- Input: forecast + risk output.
- Logic: EOQ / safety stock formulas to compute reorder point and reorder quantity.
- Output: recommendation list.

### Conversational Insight Agent
- Input: user's NL question + structured outputs from the three agents above (as context, not the raw dataset — keeps prompts small and answers grounded).
- Model: Groq API serving an open-source model (Llama 3.3 70B or Mixtral) — swappable via a single `llm_client.py` wrapper.
- Uses LangChain tool-calling to select the right structured data slice to answer from, rather than dumping all context into every prompt.

## 3. Data Flow (batch pipeline, run once or on-demand)
1. Raw CSV (Kaggle dataset) → cleaned and loaded into PostgreSQL.
2. Forecast Agent reads from DB, writes forecast table.
3. Risk Agent reads forecast + inventory table, writes risk/alert table.
4. Inventory Agent reads forecast + risk, writes recommendation table.
5. Frontend/API reads from these tables directly for dashboard views (fast, no live recompute needed).
6. Conversational Agent, on each user query, pulls relevant rows from these tables as grounding context and generates an answer via Groq.

## 4. Why This Architecture (talking points for interview)
- **Deterministic agents first, LLM last**: keeps the core numbers (forecasts, risk flags) reliable and testable; the LLM's job is explanation, not computation — mirrors how real enterprise AI systems avoid letting LLMs "do the math."
- **LangGraph orchestration**: directly maps to the JD's "agentic workflows and multi-step AI orchestration" requirement — shows a real, inspectable pipeline rather than one big prompt.
- **Swappable LLM layer**: shows engineering discipline — can point out this could run on Anthropic/OpenAI in production with a one-line change.
- **Batch + table-backed dashboard**: keeps latency low and avoids overcomplicating with real-time infra that wasn't asked for.

## 5. Deployment Architecture (Render)
Changed from the original AWS plan to Render's free tier — no billing/account overhead for a portfolio demo, and Render deploys directly from the existing Dockerfiles/docker-compose setup with minimal extra configuration.
- Backend: a Render Web Service built from `backend/Dockerfile`.
- Frontend: a Render Web Service (or Static Site) built from `frontend/Dockerfile`/`frontend/dist`.
- Database: Render's free managed Postgres, replacing the local `db` Docker service for production.
- Env vars (`DATABASE_URL`, `GROQ_API_KEY`, etc.) configured via Render's dashboard, mirroring `.env.example`.