#!/bin/sh
# Self-seeding startup: create tables, then seed + run the pipeline only if
# both (a) the DB is empty AND (b) the dataset CSV is actually present in
# this environment. Locally the CSV arrives via a bind mount
# (docker-compose). On a platform with no volume-mount equivalent (e.g.
# Render), seed the DB externally first (see README's Deployment section)
# -- the container then just finds existing data and skips straight to
# serving, same as any restart. Without this check, a deploy with no CSV
# and no data would crash-loop instead of starting an (empty) API.
set -e

python -c "from app.db.session import init_db; init_db()"

python -c "
from app.db.session import SessionLocal
from app.db.models import SalesRecord
with SessionLocal() as db:
    raise SystemExit(0 if db.query(SalesRecord).count() > 0 else 1)
" && echo "Database already seeded, skipping ingestion." || {
  if [ -f "data/raw/train.csv" ]; then
    echo "Seeding database (first run)..."
    python -m app.services.data_ingestion
    python -m app.agents.orchestrator
  else
    echo "No dataset CSV found and database is empty -- starting API unseeded. Seed it externally (see README's Deployment section)."
  fi
}

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
