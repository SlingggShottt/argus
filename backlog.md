# Argus — Backlog

Pending work, known gaps, and deferred items. Update as items complete or new ones surface.

## Build order (from CLAUDE.md, not yet done)
- [x] 1. Data ingestion + cleaning (Kaggle Store Item Demand Forecasting) — complete. 913,000 sales rows + 500 synthesized inventory rows loaded and verified in the live Postgres container.
- [x] 2. Demand Forecast Agent (XGBoost baseline) — complete. 16.79% MAPE vs. 24.94% seasonal-naive baseline on the real dataset; 15,000 forecast rows verified in Postgres.
- [x] 3. Anomaly/Risk Agent (rule-based thresholds + z-score) — complete. 87 stockout flags (55 high, 32 medium), 0 anomaly flags (verified as a genuine result, not a bug) on the real dataset.
- [x] 4. Inventory Optimization Agent (EOQ / safety stock) — complete. 500 recommendations written, EOQ/safety-stock formulas hand-checked in tests.
- [x] 5. LangGraph orchestrator tying agents together — complete. Verified end-to-end against Postgres, identical results to individually-run agents.
- [x] 6. Conversational Insight Agent (Groq-backed) — complete. Verified against real Groq API for all 3 FR-6.3 query types; found and fixed a real tool-calling reliability bug (see Known gaps, now resolved).
- [x] 7. FastAPI endpoints exposing all of the above — complete. All 5 endpoints verified via real HTTP requests against live Postgres + real Groq.
- [ ] 8. React dashboard (KPIs, alerts, chat)
- [ ] 9. Docker Compose for local run
- [ ] 10. AWS deployment (EC2 + S3, optionally RDS)

## Should-have / Nice-to-have (from PRD.md scope table)
- [ ] Deployed on AWS (Should-have — item 10 above)
- [ ] Agent reasoning trace visible in UI (Nice-to-have — depends on Phase 5/8 design; NFR-2 requires logging intermediate outputs regardless, but surfacing that in the frontend is optional stretch)

## Explicitly out of scope for v1 (from PRD.md Non-Goals / SRS constraints)
- Multi-tenant / multi-user auth system
- Real-time streaming data ingestion (batch only)
- Production-grade MLOps (model registry, retraining pipelines)
- Support for arbitrary datasets beyond the chosen schema
- Multi-dataset support

## Stretch goals (not in original docs — candidates if time allows after core build)
- [ ] RAG over historical agent outputs or docs
- [ ] MCP exposure of agent tools

## Known gaps / risks to watch
- ~~LLM tool-calling reliability with Groq-hosted open models may need prompt tuning~~ — RESOLVED in Phase 6: the model looped calling `get_forecast` repeatedly instead of answering; fixed with a stronger system prompt ("call each tool at most once... do not call the same tool again"). Good interview story: predicted risk in `docs/PRD.md`, actually hit it, fixed it, verified the fix against the real API.
- Forecast quality depends on dataset cleanliness — don't skip EDA during Phase 1.
- `sample_submission.csv` was deliberately excluded from the repo — if `test.csv`'s Kaggle-specific time-based public/private split logic matters later, revisit whether `test.csv` is even usable for our purposes (we may only need `train.csv` for a self-made holdout split, per SRS FR-2.3 "against a holdout set").
- Inventory levels are synthetic, not real (see `context.md` Deviations section for the full formula/assumptions) — worth calling out proactively in the interview before it looks like an oversight.
- Forecast model uses calendar features only, no lag/rolling-window features — a deliberate v1 simplicity call (avoids recursive multi-step forecasting complexity), documented as a known limitation, not an oversight. Candidate future improvement if time allows.
- EOQ ordering/holding cost inputs are illustrative placeholders, not real cost data (dataset has no prices at all) — same caveat category as synthetic inventory, worth mentioning proactively in the interview.
- FastAPI + SQLAlchemy + in-memory SQLite testing requires `StaticPool` (sync route handlers run in a worker thread, SQLite `:memory:` is thread-scoped by default) — documented in `context.md`, worth knowing if adding more API tests later.

## Completed
- [x] Phase 0 scaffolding: directory structure, docs moved to `docs/`, `.gitignore`, `.env.example`, `requirements.txt`, `config.py`, git initialized, dataset downloaded.
- [x] Phase 1 data ingestion: DB models/session layer (tested against SQLite + verified against live Postgres), Postgres-only `docker-compose.yml`, ingestion script (cleaning, idempotent load, inventory synthesis), 18 backend tests passing. Two real bugs found and fixed via testing against real Postgres, not just SQLite unit tests (see `context.md`).
- [x] Phase 2 Demand Forecast Agent: XGBoost model wrapper + agent, temporal holdout evaluation vs. seasonal-naive baseline, 27 backend tests passing (9 new), verified end-to-end against the real 913K-row dataset in Postgres.
- [x] Phase 3 Anomaly/Risk Agent: stockout severity tiers + rolling-window z-score anomaly detection, 37 backend tests passing (10 new), verified end-to-end against Postgres including an independent diagnostic confirming the zero-anomaly result is genuine, not a silent bug.
- [x] Phase 4 Inventory Optimization Agent: EOQ + safety-stock formulas (hand-checked in tests), 44 backend tests passing (7 new), 500 recommendations verified end-to-end and cross-checked against inventory/forecast data in Postgres.
- [x] Phase 5 LangGraph orchestrator: Forecast -> Risk -> Inventory as one StateGraph, 46 backend tests passing (2 new), verified end-to-end against Postgres with results identical to the individually-run agents.
- [x] Phase 6 Conversational Agent: swappable `llm_client.py` + tool-calling `conversational_agent.py`, 55 backend tests passing (10 new, all mocked/no real API calls), verified against the real Groq API for all 3 FR-6.3 query types. Found and fixed a real tool-calling loop bug via testing against the live API, not just mocks.
- [x] Phase 7 FastAPI endpoints: 4 REST endpoints + health check, 61 backend tests passing (6 new), verified via real HTTP requests (curl) against the live server, Postgres, and Groq. Found and fixed a real FastAPI+SQLite-in-memory threading bug via testing.
