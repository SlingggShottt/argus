"""Integration test for the LangGraph orchestrator: seeds sales + inventory
into in-memory SQLite, runs the full Forecast -> Risk -> Inventory pipeline,
and checks all three outputs and DB tables end up populated and consistent."""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents import orchestrator
from app.config import settings
from app.db.models import Base, Forecast, Inventory, Recommendation, RiskFlag, SalesRecord


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _seed(db, num_days=40):
    start = date(2017, 1, 1)
    for i in range(num_days):
        db.add(SalesRecord(date=start + timedelta(days=i), store_id=1, item_id=1, sales=10 + (i % 7)))
    db.add(
        Inventory(
            store_id=1,
            item_id=1,
            avg_daily_demand=10,
            current_stock=20,
            as_of_date=start + timedelta(days=num_days - 1),
        )
    )
    db.commit()


def test_run_executes_full_pipeline_in_order(db_session, monkeypatch):
    monkeypatch.setattr(settings, "forecast_horizon_days", 5)
    _seed(db_session)

    output = orchestrator.run(db_session)

    assert output.forecast.rows_written == 5
    assert output.inventory.rows_written == 1
    assert db_session.query(Forecast).count() == 5
    assert db_session.query(Recommendation).count() == 1
    # risk depends on the seeded scenario; just confirm consistency with output
    assert db_session.query(RiskFlag).count() == output.risk.rows_written


def test_run_is_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "forecast_horizon_days", 5)
    _seed(db_session)

    orchestrator.run(db_session)
    orchestrator.run(db_session)

    assert db_session.query(Forecast).count() == 5
    assert db_session.query(Recommendation).count() == 1
