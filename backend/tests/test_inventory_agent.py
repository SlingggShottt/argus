"""Tests for the Inventory Optimization Agent: forecast demand stats,
EOQ/safety-stock formula correctness (hand-checked), and DB wiring."""

from datetime import date, timedelta

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents import inventory_agent
from app.db.models import Base, Forecast, Recommendation

# ---- _load_forecast_demand_stats ----


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_load_forecast_demand_stats_computes_mean_and_std(db_session):
    today = date(2018, 1, 1)
    db_session.add_all(
        [
            Forecast(store_id=1, item_id=1, forecast_date=today, predicted_sales=8, horizon_days=2),
            Forecast(store_id=1, item_id=1, forecast_date=today + timedelta(days=1), predicted_sales=12, horizon_days=2),
        ]
    )
    db_session.commit()

    stats = inventory_agent._load_forecast_demand_stats(db_session)

    assert len(stats) == 1
    row = stats.iloc[0]
    assert row["avg_daily_demand"] == pytest.approx(10.0)
    assert row["demand_std"] == pytest.approx(2.8284, abs=0.001)  # sqrt(((8-10)^2+(12-10)^2)/1)


def test_load_forecast_demand_stats_empty_when_no_forecasts(db_session):
    stats = inventory_agent._load_forecast_demand_stats(db_session)

    assert stats.empty


# ---- _compute_recommendations (hand-checked formulas) ----


def test_compute_recommendations_matches_hand_calculation():
    # avg_daily_demand=10, demand_std=2, using default settings
    # (lead_time_days=7, service_level_z_score=1.65, eoq_ordering_cost=50,
    # eoq_holding_cost_per_unit=2):
    # safety_stock = 1.65 * 2 * sqrt(7) = 8.7309
    # reorder_point = 10*7 + 8.7309 = 78.7309
    # eoq = sqrt((2 * 3650 * 50) / 2) = sqrt(182500) = 427.2002
    stats = pd.DataFrame({"store_id": [1], "item_id": [1], "avg_daily_demand": [10.0], "demand_std": [2.0]})

    recommendations = inventory_agent._compute_recommendations(stats)

    assert len(recommendations) == 1
    rec = recommendations[0]
    assert rec["reorder_point"] == pytest.approx(78.7309, abs=0.01)
    assert rec["reorder_quantity"] == pytest.approx(427.2002, abs=0.01)


def test_compute_recommendations_zero_variance_gives_zero_safety_stock():
    stats = pd.DataFrame({"store_id": [1], "item_id": [1], "avg_daily_demand": [10.0], "demand_std": [0.0]})

    recommendations = inventory_agent._compute_recommendations(stats)

    # No demand variability -> reorder_point is exactly avg_daily_demand * lead_time_days
    assert recommendations[0]["reorder_point"] == pytest.approx(70.0)


# ---- run() end-to-end against in-memory SQLite ----


def _seed_forecasts(db, store_item_pairs, horizon_days=30, base_demand=10):
    today = date(2018, 1, 1)
    for store_id, item_id in store_item_pairs:
        for i in range(horizon_days):
            db.add(
                Forecast(
                    store_id=store_id,
                    item_id=item_id,
                    forecast_date=today + timedelta(days=i),
                    predicted_sales=base_demand + (i % 5),  # some natural variation
                    horizon_days=horizon_days,
                )
            )
    db.commit()


def test_run_writes_one_recommendation_per_sku(db_session):
    _seed_forecasts(db_session, [(1, 1), (2, 3)])

    output = inventory_agent.run(db_session)

    assert output.rows_written == 2
    assert db_session.query(Recommendation).count() == 2


def test_run_recommendations_are_positive(db_session):
    _seed_forecasts(db_session, [(1, 1)])

    inventory_agent.run(db_session)

    rec = db_session.query(Recommendation).one()
    assert rec.reorder_point > 0
    assert rec.reorder_quantity > 0


def test_run_is_idempotent(db_session):
    _seed_forecasts(db_session, [(1, 1)])

    inventory_agent.run(db_session)
    inventory_agent.run(db_session)

    assert db_session.query(Recommendation).count() == 1
