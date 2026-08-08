"""Tests for the ingestion service: CSV cleaning/validation and DB loading
logic. Uses small in-memory CSVs and an in-memory SQLite DB — these test our
own logic, not pandas or Postgres itself."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, Inventory, SalesRecord
from app.services.data_ingestion import (
    load_and_clean_sales,
    load_sales_records,
    synthesize_inventory,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _write_csv(tmp_path: Path, rows: str) -> Path:
    csv_path = tmp_path / "train.csv"
    csv_path.write_text("date,store,item,sales\n" + rows)
    return csv_path


def test_load_and_clean_sales_happy_path(tmp_path):
    csv_path = _write_csv(tmp_path, "2013-01-01,1,1,13\n2013-01-02,1,1,11\n")

    df = load_and_clean_sales(csv_path)

    assert list(df.columns) == ["date", "store_id", "item_id", "sales"]
    assert len(df) == 2
    assert df.iloc[0]["date"] == date(2013, 1, 1)


def test_load_and_clean_sales_drops_invalid_rows(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        "2013-01-01,1,1,13\n"
        "not-a-date,1,1,10\n"
        "2013-01-03,1,1,-5\n"
        "2013-01-01,1,1,13\n",
    )

    df = load_and_clean_sales(csv_path)

    assert len(df) == 1


def test_load_and_clean_sales_raises_on_missing_columns(tmp_path):
    csv_path = tmp_path / "train.csv"
    csv_path.write_text("date,store,sales\n2013-01-01,1,13\n")

    with pytest.raises(ValueError):
        load_and_clean_sales(csv_path)


def test_load_and_clean_sales_raises_if_all_rows_invalid(tmp_path):
    csv_path = _write_csv(tmp_path, "not-a-date,1,1,10\n")

    with pytest.raises(ValueError):
        load_and_clean_sales(csv_path)


def test_load_sales_records_is_idempotent(db_session):
    df = pd.DataFrame(
        {
            "date": [date(2013, 1, 1), date(2013, 1, 2)],
            "store_id": [1, 1],
            "item_id": [1, 1],
            "sales": [13, 11],
        }
    )

    load_sales_records(db_session, df)
    load_sales_records(db_session, df)  # re-run must not duplicate

    assert db_session.query(SalesRecord).count() == 2


def test_synthesize_inventory_creates_one_row_per_sku(db_session):
    df = pd.DataFrame(
        {
            "date": [date(2013, 1, 1), date(2013, 1, 2), date(2013, 1, 1)],
            "store_id": [1, 1, 2],
            "item_id": [1, 1, 1],
            "sales": [10, 20, 5],
        }
    )

    synthesize_inventory(db_session, df)

    rows = db_session.query(Inventory).all()
    assert len(rows) == 2  # (store 1, item 1) and (store 2, item 1)
    for row in rows:
        assert row.current_stock > 0
        assert row.avg_daily_demand > 0


def test_synthesize_inventory_is_reproducible(db_session):
    df = pd.DataFrame({"date": [date(2013, 1, 1)], "store_id": [1], "item_id": [1], "sales": [10]})

    synthesize_inventory(db_session, df)
    first_stock = db_session.query(Inventory).one().current_stock

    synthesize_inventory(db_session, df)  # re-run, same seed
    second_stock = db_session.query(Inventory).one().current_stock

    assert first_stock == second_stock
