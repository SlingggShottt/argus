"""Tests for the Risk/Anomaly Agent: stockout threshold logic, rolling-window
z-score anomaly detection, and DB wiring (idempotency, correct row counts)."""

from datetime import date, timedelta

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents import risk_agent
from app.db.models import Base, Forecast, Inventory, RiskFlag, SalesRecord

# ---- _stockout_risk_flags ----


def test_stockout_flags_high_severity_when_demand_exceeds_stock():
    demand_df = pd.DataFrame({"store_id": [1], "item_id": [1], "projected_demand": [100.0]})
    inventory_df = pd.DataFrame({"store_id": [1], "item_id": [1], "current_stock": [80.0]})

    flags = risk_agent._stockout_risk_flags(demand_df, inventory_df)

    assert len(flags) == 1
    assert flags[0]["severity"] == "high"
    assert flags[0]["risk_type"] == "stockout"


def test_stockout_flags_medium_severity_near_threshold():
    # ratio = 95/100 = 0.95, between default threshold 0.9 and 1.0
    demand_df = pd.DataFrame({"store_id": [1], "item_id": [1], "projected_demand": [95.0]})
    inventory_df = pd.DataFrame({"store_id": [1], "item_id": [1], "current_stock": [100.0]})

    flags = risk_agent._stockout_risk_flags(demand_df, inventory_df)

    assert len(flags) == 1
    assert flags[0]["severity"] == "medium"


def test_stockout_flags_none_when_well_stocked():
    demand_df = pd.DataFrame({"store_id": [1], "item_id": [1], "projected_demand": [10.0]})
    inventory_df = pd.DataFrame({"store_id": [1], "item_id": [1], "current_stock": [100.0]})

    flags = risk_agent._stockout_risk_flags(demand_df, inventory_df)

    assert flags == []


def test_stockout_flags_high_severity_when_zero_stock():
    demand_df = pd.DataFrame({"store_id": [1], "item_id": [1], "projected_demand": [5.0]})
    inventory_df = pd.DataFrame({"store_id": [1], "item_id": [1], "current_stock": [0.0]})

    flags = risk_agent._stockout_risk_flags(demand_df, inventory_df)

    assert len(flags) == 1
    assert flags[0]["severity"] == "high"


# ---- _anomaly_flags ----


def _sales_df(store_id, item_id, values, start=date(2017, 1, 1)):
    return pd.DataFrame(
        {
            "store_id": [store_id] * len(values),
            "item_id": [item_id] * len(values),
            "date": [start + timedelta(days=i) for i in range(len(values))],
            "sales": values,
        }
    )


def test_anomaly_flags_detects_spike():
    # mildly-varying 60-day baseline (mean ~10), then a 7-day recent window at 50
    baseline = [8, 9, 10, 11, 12, 10, 9] * 9  # 63 days, trimmed to 60 below
    df = _sales_df(1, 1, baseline[:60] + [50] * 7)

    flags = risk_agent._anomaly_flags(df)

    assert len(flags) == 1
    assert flags[0]["risk_type"] == "anomaly"
    assert "spike" in flags[0]["details"]


def test_anomaly_flags_detects_drop():
    baseline = [8, 9, 10, 11, 12, 10, 9] * 9
    df = _sales_df(1, 1, baseline[:60] + [1] * 7)

    flags = risk_agent._anomaly_flags(df)

    assert len(flags) == 1
    assert "drop" in flags[0]["details"]


def test_anomaly_flags_none_when_stable():
    values = ([8, 9, 10, 11, 12, 10, 9] * 10)[:67]  # same mild pattern throughout
    df = _sales_df(1, 1, values)

    flags = risk_agent._anomaly_flags(df)

    assert flags == []


def test_anomaly_flags_skips_zero_variance_baseline():
    # constant baseline (std=0) makes z-score undefined -> must not crash or false-flag
    df = _sales_df(1, 1, [10] * 60 + [10] * 7)

    flags = risk_agent._anomaly_flags(df)

    assert flags == []


# ---- run() end-to-end against in-memory SQLite ----


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


BASELINE_PATTERN = [8, 9, 10, 11, 12, 10, 9]  # small natural variation, mean ~9.86


def _seed_run_scenario(db):
    """SKU (1,1): stockout risk (thin stock, stable demand). SKU (2,2): demand
    spike, plenty of stock (no stockout). SKU (3,3): healthy, stable, well
    stocked -> should produce nothing."""
    today = date(2017, 12, 31)
    baseline_dates = [today - timedelta(days=d) for d in range(66, 6, -1)]  # 60 days
    recent_dates = [today - timedelta(days=d) for d in range(6, -1, -1)]  # 7 days

    def add_sales(store_id, item_id, recent_value):
        for i, d in enumerate(baseline_dates):
            db.add(
                SalesRecord(
                    date=d, store_id=store_id, item_id=item_id, sales=BASELINE_PATTERN[i % len(BASELINE_PATTERN)]
                )
            )
        for d in recent_dates:
            db.add(SalesRecord(date=d, store_id=store_id, item_id=item_id, sales=recent_value))

    def add_forecast(store_id, item_id, predicted_sales):
        for i in range(1, 8):  # matches default lead_time_days=7
            db.add(
                Forecast(
                    store_id=store_id,
                    item_id=item_id,
                    forecast_date=today + timedelta(days=i),
                    predicted_sales=predicted_sales,
                    horizon_days=7,
                )
            )

    add_sales(1, 1, recent_value=10)
    db.add(Inventory(store_id=1, item_id=1, avg_daily_demand=10, current_stock=5, as_of_date=today))
    add_forecast(1, 1, predicted_sales=10)

    add_sales(2, 2, recent_value=80)
    db.add(Inventory(store_id=2, item_id=2, avg_daily_demand=10, current_stock=1000, as_of_date=today))
    add_forecast(2, 2, predicted_sales=10)

    add_sales(3, 3, recent_value=10)
    db.add(Inventory(store_id=3, item_id=3, avg_daily_demand=10, current_stock=1000, as_of_date=today))
    add_forecast(3, 3, predicted_sales=10)

    db.commit()


def test_run_flags_stockout_and_anomaly_correctly(db_session):
    _seed_run_scenario(db_session)

    output = risk_agent.run(db_session)

    flags = db_session.query(RiskFlag).all()
    stockout_flags = [f for f in flags if f.risk_type == "stockout"]
    anomaly_flags = [f for f in flags if f.risk_type == "anomaly"]

    assert output.rows_written == len(flags)
    assert len(stockout_flags) == 1
    assert (stockout_flags[0].store_id, stockout_flags[0].item_id) == (1, 1)

    assert len(anomaly_flags) == 1
    assert (anomaly_flags[0].store_id, anomaly_flags[0].item_id) == (2, 2)

    assert [f for f in flags if f.store_id == 3] == []


def test_run_is_idempotent(db_session):
    _seed_run_scenario(db_session)

    risk_agent.run(db_session)
    risk_agent.run(db_session)

    assert db_session.query(RiskFlag).count() == 2  # 1 stockout + 1 anomaly, not duplicated
