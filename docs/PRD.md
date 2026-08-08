# Product Requirements Document — Argus

## 1. Problem Statement
Enterprises managing large product catalogs struggle to answer basic but high-stakes questions fast: Which SKUs are about to stock out? Which locations show abnormal demand? What should we reorder, and when? Analysts spend hours manually pulling reports before a decision gets made — by the time insight arrives, the window to act has often passed.

## 2. Target User
A supply chain / operations analyst or manager at a mid-to-large retail/CPG enterprise who needs fast, explainable answers without writing SQL or building their own forecasting pipeline.

## 3. Goals
- Reduce time-to-insight for demand and inventory questions from hours to seconds.
- Surface risk (stockouts, demand anomalies) proactively instead of reactively.
- Let a non-technical user query the system in plain English and get a grounded, data-backed answer.

## 4. Non-Goals (out of scope for v1)
- Multi-tenant / multi-user auth system
- Real-time streaming data ingestion (batch is fine)
- Production-grade MLOps (model registry, retraining pipelines)
- Support for arbitrary datasets beyond the chosen schema

## 5. Core User Stories
1. As an analyst, I want to see a dashboard of demand forecasts per SKU/store so I can plan inventory ahead of time.
2. As an analyst, I want to be alerted when a SKU shows anomalous demand or stockout risk so I can act before it becomes a problem.
3. As an analyst, I want inventory reorder recommendations (quantity + timing) so I don't have to calculate safety stock manually.
4. As an analyst, I want to ask questions in plain English ("which SKUs are at risk next month?") and get a direct answer grounded in the underlying data.
5. As an interviewer/evaluator, I want to see the reasoning trace of the agent pipeline so I understand it isn't a black box.

## 6. Success Metrics (for this project, framed like a real business case)
- Forecast accuracy: MAPE within an acceptable range for the chosen dataset (benchmark against a naive baseline).
- Reduction in "manual analysis steps" a user would otherwise take (framed qualitatively — e.g., "5 manual steps → 1 query").
- Working end-to-end demo: raw data → forecast → risk flag → recommendation → NL answer, in under a defined latency (e.g., a few seconds for the query agent).

## 7. Key Features (v1 scope)
| Feature | Priority |
|---|---|
| Demand forecasting per SKU/store | Must-have |
| Anomaly/risk detection | Must-have |
| Inventory reorder recommendation | Must-have |
| Agent orchestration layer (LangGraph) | Must-have |
| Conversational query interface | Must-have |
| Dashboard (KPIs, charts, alerts) | Must-have |
| Deployed on AWS | Should-have |
| Agent reasoning trace visible in UI | Nice-to-have |
| Multi-dataset support | Out of scope |

## 8. Timeline
1 week, per the build plan in `CLAUDE.md`.

## 9. Risks
- LLM tool-calling reliability with free/open models (Groq-hosted Llama/Mixtral) may need prompt tuning — budget extra time on Day 4.
- Forecast quality depends heavily on dataset cleanliness — don't skip EDA on Day 1.