#!/bin/sh
# Self-seeding startup: create tables, then run the ingestion + agent
# pipeline only if the DB is empty (idempotent agents make this safe to
# skip on restart -- Postgres data persists in its named volume). Matches
# NFR-3: docker-compose up alone, no manual setup beyond .env.
set -e

python -c "from app.db.session import init_db; init_db()"

python -c "
from app.db.session import SessionLocal
from app.db.models import SalesRecord
with SessionLocal() as db:
    raise SystemExit(0 if db.query(SalesRecord).count() > 0 else 1)
" && echo "Database already seeded, skipping ingestion." || {
  echo "Seeding database (first run)..."
  python -m app.services.data_ingestion
  python -m app.agents.orchestrator
}

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
