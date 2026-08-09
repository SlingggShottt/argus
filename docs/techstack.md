# Tech Stack — Argus

## Backend
| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Ecosystem fit for ML + agents |
| API framework | FastAPI | Async, auto-generated OpenAPI docs, fast to build |
| Agent orchestration | LangGraph (LangChain ecosystem) | Explicit graph-based multi-agent orchestration, matches JD's "agentic pipelines" requirement |
| Forecasting model | XGBoost (primary) or Prophet (if seasonality-heavy) | Explainable, fast to train, well-understood — better interview story than a black-box deep model |
| Anomaly detection | Statistical (z-score / rolling stats) | Simple, explainable, fast to implement in a week |
| Inventory optimization | Classical EOQ / safety stock formulas | Deterministic, no ML needed, easy to defend in interview |
| Database | PostgreSQL | Relational fit for tabular sales/inventory data, production-realistic choice |
| ORM | SQLAlchemy | Standard, works cleanly with FastAPI |
| LLM provider | Groq API (Llama 3.3 70B / Mixtral) | Free tier, fast inference, genuinely open-source models, supports tool-calling |
| LLM fallback | Ollama (local) | Offline story if Groq free tier is a concern during demo |

## Frontend
| Component | Choice
|---|---|---|
| Framework | React 
| Build tool | Vite | Fast dev loop |
| Charts | Recharts | Simple, good enough for forecast/KPI visualization |
| Styling | Tailwind CSS | Fast to build consistent UI without custom CSS overhead |
| State/data fetching | React Query (TanStack Query) | Clean handling of API calls, caching, loading states |

## Infrastructure
| Component | Choice | Why |
|---|---|---|
| Containerization | Docker + Docker Compose | One-command local run, matches existing workflow |
| Cloud | Render (free tier) | Free hosting for backend + frontend + Postgres, no AWS billing/account overhead for a portfolio demo. Changed from the original AWS plan — see context.md. |
| CI/CD | Github Actions

## Dataset
- **Kaggle Store Item Demand Forecasting** (or equivalent public dataset) — clean, well-documented, right size for a week-long build without heavy preprocessing overhead.

## Dev Tools
| Tool | Purpose |
|---|---|
| pytest | Backend testing |
| ruff / black | Python linting/formatting |
| eslint / prettier | Frontend linting/formatting |
| python-dotenv | Environment variable management |