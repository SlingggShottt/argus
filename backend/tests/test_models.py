"""Structural tests for the SQLAlchemy models: table creation, constraints,
and round-trip inserts against an in-memory SQLite DB. SQLite is fine here
because nothing in models.py uses a Postgres-specific type — these tests
check schema correctness, not Postgres itself."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Base, Inventory, RiskFlag, SalesRecord


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_all_tables_created(db_session):
    table_names = set(Base.metadata.tables.keys())
    assert table_names == {
        "sales_records",
        "inventory",
        "forecasts",
        "risk_flags",
        "recommendations",
    }


def test_sales_record_insert_and_query(db_session):
    db_session.add(SalesRecord(date=date(2013, 1, 1), store_id=1, item_id=1, sales=13))
    db_session.commit()

    fetched = db_session.query(SalesRecord).one()
    assert fetched.store_id == 1
    assert fetched.item_id == 1
    assert fetched.sales == 13


def test_sales_record_rejects_duplicate_date_store_item(db_session):
    db_session.add(SalesRecord(date=date(2013, 1, 1), store_id=1, item_id=1, sales=13))
    db_session.commit()

    db_session.add(SalesRecord(date=date(2013, 1, 1), store_id=1, item_id=1, sales=99))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_inventory_rejects_duplicate_sku(db_session):
    db_session.add(
        Inventory(
            store_id=1,
            item_id=1,
            avg_daily_demand=10.0,
            current_stock=70.0,
            as_of_date=date(2017, 12, 31),
        )
    )
    db_session.commit()

    db_session.add(
        Inventory(
            store_id=1,
            item_id=1,
            avg_daily_demand=12.0,
            current_stock=84.0,
            as_of_date=date(2017, 12, 31),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_risk_flag_round_trip(db_session):
    db_session.add(
        RiskFlag(
            store_id=1,
            item_id=1,
            risk_type="stockout",
            severity="high",
            details="Forecasted demand over lead time exceeds current stock.",
        )
    )
    db_session.commit()

    fetched = db_session.query(RiskFlag).one()
    assert fetched.risk_type == "stockout"
    assert fetched.created_at is not None
