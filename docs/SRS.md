# Software Requirements Specification — Argus

## 1. Introduction

### 1.1 Purpose
Defines functional and non-functional requirements for Argus, an agentic AI decision-intelligence platform for supply chain demand forecasting and inventory risk management.

### 1.2 Scope
Argus takes historical sales/inventory data as input and produces: demand forecasts, risk/anomaly flags, inventory recommendations, and natural-language answers to user queries — delivered via a web dashboard and API.

### 1.3 Definitions
- **Agent**: An autonomous module (rule-based or LLM-backed) responsible for one task in the pipeline.
- **Orchestrator**: The component that sequences agent calls and passes data between them.
- **SKU**: Stock Keeping Unit — a unique product/store combination.

## 2. Overall Description

### 2.1 Product Perspective
Standalone web application: React (JavaScript) frontend, FastAPI backend, PostgreSQL for storage, a multi-agent orchestration layer (LangGraph) coordinating forecasting, risk detection, optimization, and an LLM-backed query agent.

### 2.2 User Classes
- **Primary user**: Supply chain analyst/manager (dashboard + chat interface)
- **Secondary user**: Developer/evaluator inspecting API directly or reviewing agent reasoning traces

### 2.3 Operating Environment
- Backend: Python 3.11+, FastAPI, Docker container
- Frontend: React (JavaScript), served via Docker/Nginx or Vite dev server
- Database: PostgreSQL (containerized or AWS RDS)
- Deployment target: AWS (EC2, optionally RDS + S3)

## 3. Functional Requirements

### FR-1: Data Ingestion
- FR-1.1: System shall ingest the Kaggle Store Item Demand Forecasting dataset (or equivalent) into PostgreSQL.
- FR-1.2: System shall clean and validate data (missing values, date parsing, type checks) before use.

### FR-2: Demand Forecasting
- FR-2.1: System shall generate a demand forecast per store-item combination for a configurable future horizon.
- FR-2.2: System shall expose forecast results via API.
- FR-2.3: System shall report a model accuracy metric (e.g., MAPE) against a holdout set.

### FR-3: Risk / Anomaly Detection
- FR-3.1: System shall flag store-item combinations where projected demand exceeds available/projected inventory (stockout risk).
- FR-3.2: System shall flag statistically anomalous demand patterns (e.g., sudden spikes/drops beyond a threshold).

### FR-4: Inventory Optimization
- FR-4.1: System shall compute a recommended reorder quantity and reorder point per SKU using forecast output (e.g., EOQ / safety stock formulas).

### FR-5: Agent Orchestration
- FR-5.1: System shall coordinate Forecast, Risk, and Inventory agents through a defined orchestrator (LangGraph) rather than ad hoc function calls.
- FR-5.2: Orchestrator shall produce a combined output object consumable by both the API and the conversational agent.

### FR-6: Conversational Query Interface
- FR-6.1: System shall accept natural-language questions from the user via chat UI.
- FR-6.2: System shall answer using an LLM (Groq-hosted open-source model) grounded in the orchestrator's output — not free-form hallucination.
- FR-6.3: System shall handle at minimum: risk queries ("which SKUs are at risk"), forecast queries ("what's the forecast for X"), and recommendation queries ("what should I reorder").

### FR-7: Dashboard
- FR-7.1: System shall display forecast charts, a risk/alert list, and reorder recommendations.
- FR-7.2: System shall provide a chat panel for natural-language queries.

### FR-8: API
- FR-8.1: All core functions (forecast, risk, recommendation, query) shall be exposed as documented REST endpoints (FastAPI auto-generated OpenAPI docs).

## 4. Non-Functional Requirements

- NFR-1 (Performance): Dashboard queries should return within a few seconds for the chosen dataset size.
- NFR-2 (Explainability): Agent reasoning/outputs should be inspectable, not a pure black box — log intermediate agent outputs.
- NFR-3 (Portability): Entire stack must run via `docker-compose up` with no manual setup beyond `.env` configuration.
- NFR-4 (Cost): LLM usage must run on free-tier/open-source infrastructure (Groq free tier or local Ollama fallback).
- NFR-5 (Maintainability): Code shall follow `style_guide.md`; agents shall be modular and independently testable.
- NFR-6 (Deployability): System shall be deployable to AWS within the project's automation scripts (mirroring existing AWS lab conventions — resource prefixes, teardown scripts).

## 5. Constraints
- One-week build timeline.
- Free/open-source LLM only (no paid API dependency for the core demo).
- Single dataset/schema supported (no generalization requirement for v1).

## 6. Assumptions
- Dataset is static/batch, not a live feed.
- Single-user system, no auth required for v1.