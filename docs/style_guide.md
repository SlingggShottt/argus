# Style Guide — Argus

## General Principles
- Prefer clarity over cleverness. Code should read like a straightforward explanation of what it does.
- No dead code, no commented-out blocks left in commits.
- Every agent/module should be independently runnable/testable — avoid tight coupling that makes debugging one agent require running the whole pipeline.

## Python (Backend)
- Follow PEP8; enforce with `ruff` + `black`.
- Type hints required on all function signatures.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- File/module naming: one agent per file under `app/agents/` (e.g., `forecast_agent.py`, `risk_agent.py`).
- Docstrings: one-line summary only, unless logic is genuinely non-obvious (e.g., the EOQ formula deserves a short comment on inputs/assumptions). No boilerplate docstrings that restate the function name.
- Error handling: agents should fail loudly with clear exceptions during development — no silent `except: pass`.
- Config: all tunables (forecast horizon, risk thresholds, DB URL, API keys) via environment variables / a single `config.py`, never hardcoded inline.

## JavaScript / React (Frontend)
- Functional components + hooks only, no class components.
- Naming: `PascalCase` for components, `camelCase` for functions/variables, component files named after the component (`RiskAlertList.jsx`).
- One component per file. Shared shape/type expectations documented via JSDoc comments or PropTypes where it aids clarity — no TypeScript compiler, so keep prop contracts explicit in comments.
- API calls centralized in `src/api/` — components never call `fetch` directly.
- Keep components presentational where possible; push data-fetching logic into hooks (e.g., `useForecastData.js`).

## Git Conventions
- Branch naming: `feature/<short-name>`, `fix/<short-name>`.
- Commit messages: imperative mood, short summary line (e.g., `Add EOQ calculation to inventory agent`), no filler like "misc changes."
- Commit early and often per agent/module — this also gives a clean commit history to walk through in the interview if asked.

## API Design
- REST endpoints, plural nouns (`/api/forecasts`, `/api/risks`, `/api/recommendations`).
- Consistent response shape: `{ "data": ..., "meta": ... }` for list endpoints.
- All endpoints documented via FastAPI's auto-generated OpenAPI schema — don't write separate manual API docs.

## Agent Design Conventions
- Every agent exposes a single clear entrypoint function (e.g., `run(input: ForecastInput) -> ForecastOutput`) with typed input/output — makes the orchestrator graph easy to read and easy to explain in an interview.
- Deterministic agents (Forecast, Risk, Inventory) must not call the LLM — keep the LLM boundary strictly at the Conversational Agent.
- Log agent inputs/outputs at INFO level during development for explainability and debugging.

## Documentation
- Keep `README.md` up to date with: problem statement (2-3 sentences), architecture diagram (reuse from `design_architecture.md`), setup instructions, and a short "results" section (forecast accuracy, demo screenshot/GIF).
- Write in plain, direct language — no marketing tone, no unnecessary superlatives. State what it does and how well it works.