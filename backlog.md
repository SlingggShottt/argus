# Argus — Backlog

Pending work, known gaps, and deferred items. Update as items complete or new ones surface.

## Build order (from CLAUDE.md, not yet done)
- [ ] 1. Data ingestion + cleaning (Kaggle Store Item Demand Forecasting) — in progress (DB models done, ingestion script + inventory synthesis pending)
- [ ] 2. Demand Forecast Agent (XGBoost baseline)
- [ ] 3. Anomaly/Risk Agent (rule-based thresholds + z-score)
- [ ] 4. Inventory Optimization Agent (EOQ / safety stock)
- [ ] 5. LangGraph orchestrator tying agents together
- [ ] 6. Conversational Insight Agent (Groq-backed) — needs Groq API key first
- [ ] 7. FastAPI endpoints exposing all of the above
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
- LLM tool-calling reliability with Groq-hosted open models may need prompt tuning — budget extra time when we hit Phase 6 (per PRD Risks section).
- Forecast quality depends on dataset cleanliness — don't skip EDA during Phase 1.
- `sample_submission.csv` was deliberately excluded from the repo — if `test.csv`'s Kaggle-specific time-based public/private split logic matters later, revisit whether `test.csv` is even usable for our purposes (we may only need `train.csv` for a self-made holdout split, per SRS FR-2.3 "against a holdout set").
- Inventory levels are synthetic, not real (see `context.md` Deviations section for the full formula/assumptions) — worth calling out proactively in the interview before it looks like an oversight.

## Completed
- [x] Phase 0 scaffolding: directory structure, docs moved to `docs/`, `.gitignore`, `.env.example`, `requirements.txt`, `config.py`, git initialized, dataset downloaded.
