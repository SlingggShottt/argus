"""Integration-style test for the Forecast Agent: seeds synthetic sales into
an in-memory SQLite DB, runs the full agent, and checks the DB + typed
output. Tests that the pipeline wires together and writes what it claims —
not forecast quality, which would need a much larger, realistic dataset."""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents import forecast_agent
from app.config import settings
from app.db.models import Base, Forecast, SalesRecord


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _seed_sales(db, store_item_pairs, num_days, start=date(2017, 1, 1)):
    records = []
    for store_id, item_id in store_item_pairs:
        for i in range(num_days):
            d = start + timedelta(days=i)
            records.append(SalesRecord(date=d, store_id=store_id, item_id=item_id, sales=10 + (i % 7)))
    db.add_all(records)
    db.commit()


def test_run_writes_forecast_rows_for_every_sku(db_session, monkeypatch):
    monkeypatch.setattr(settings, "forecast_horizon_days", 5)
    _seed_sales(db_session, [(1, 1), (2, 3)], num_days=40)

    output = forecast_agent.run(db_session)

    assert output.horizon_days == 5
    assert output.rows_written == 2 * 5  # 2 SKUs x 5-day horizon
    assert db_session.query(Forecast).count() == 2 * 5


def test_run_output_mape_values_are_finite(db_session, monkeypatch):
    monkeypatch.setattr(settings, "forecast_horizon_days", 5)
    _seed_sales(db_session, [(1, 1)], num_days=40)

    output = forecast_agent.run(db_session)

    assert output.xgboost_mape >= 0
    assert output.naive_mape >= 0


def test_run_is_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "forecast_horizon_days", 5)
    _seed_sales(db_session, [(1, 1)], num_days=40)

    forecast_agent.run(db_session)
    forecast_agent.run(db_session)  # re-run must not duplicate

    assert db_session.query(Forecast).count() == 5
