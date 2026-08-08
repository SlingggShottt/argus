"""Loads the Kaggle Store Item Demand Forecasting CSV into Postgres and
synthesizes a current-inventory snapshot. The dataset has no real inventory
field — see context.md's Deviations section for the exact formula and why."""

import logging
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Inventory, SalesRecord

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"date", "store", "item", "sales"}


def load_and_clean_sales(csv_path: Path) -> pd.DataFrame:
    """Reads the raw CSV, validates it, and returns a cleaned DataFrame with
    columns (date, store_id, item_id, sales) ready to load. Fails loudly if
    required columns are missing or nothing survives cleaning."""
    df = pd.read_csv(csv_path)

    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {missing_columns}")

    df = df.rename(columns={"store": "store_id", "item": "item_id"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    before = len(df)
    df = df.dropna(subset=["date", "store_id", "item_id", "sales"])
    df = df[df["sales"] >= 0]
    df = df.drop_duplicates(subset=["date", "store_id", "item_id"], keep="first")
    dropped = before - len(df)
    if dropped:
        logger.info("Dropped %d invalid/duplicate rows during cleaning", dropped)

    if df.empty:
        raise ValueError("No valid rows remained after cleaning — check the source CSV.")

    df["store_id"] = df["store_id"].astype(int)
    df["item_id"] = df["item_id"].astype(int)
    df["sales"] = df["sales"].astype(int)

    return df[["date", "store_id", "item_id", "sales"]]


def _to_native_records(df: pd.DataFrame) -> list[dict]:
    """Converts a DataFrame to a list of dicts with native Python types.
    Needed because psycopg2 can't adapt numpy scalar types (e.g. numpy.int64)
    on its own — pandas dtypes leak through DataFrame.to_dict() otherwise."""
    records = df.to_dict(orient="records")
    return [{key: (value.item() if hasattr(value, "item") else value) for key, value in record.items()} for record in records]


def load_sales_records(db: Session, df: pd.DataFrame) -> None:
    """Replaces sales_records with the cleaned DataFrame. Deleting first keeps
    re-running ingestion idempotent instead of erroring on duplicate keys."""
    db.query(SalesRecord).delete()
    db.bulk_insert_mappings(SalesRecord, _to_native_records(df))
    db.commit()
    logger.info("Loaded %d sales records", len(df))


def synthesize_inventory(db: Session, df: pd.DataFrame) -> None:
    """Generates a static current-stock snapshot per store-item: current_stock
    = trailing avg daily demand x a seeded-random days-of-cover factor. See
    context.md for the full rationale — this is a documented assumption, not
    real inventory data."""
    max_date = df["date"].max()
    lookback_start = max_date - timedelta(days=settings.inventory_lookback_days - 1)
    recent = df[df["date"] >= lookback_start]

    avg_demand = (
        recent.groupby(["store_id", "item_id"])["sales"]
        .mean()
        .reset_index()
        .rename(columns={"sales": "avg_daily_demand"})
    )

    rng = np.random.default_rng(settings.inventory_random_seed)
    days_of_cover = rng.uniform(
        settings.inventory_days_of_cover_min,
        settings.inventory_days_of_cover_max,
        size=len(avg_demand),
    )
    avg_demand["current_stock"] = avg_demand["avg_daily_demand"] * days_of_cover
    avg_demand["as_of_date"] = max_date

    db.query(Inventory).delete()
    db.bulk_insert_mappings(Inventory, _to_native_records(avg_demand))
    db.commit()
    logger.info("Synthesized inventory snapshot for %d store-items", len(avg_demand))


def run_ingestion(db: Session, csv_path: Path) -> None:
    """Entrypoint: clean the CSV, load sales, synthesize inventory."""
    df = load_and_clean_sales(csv_path)
    load_sales_records(db, df)
    synthesize_inventory(db, df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db.session import SessionLocal

    default_csv_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "train.csv"
    with SessionLocal() as session:
        run_ingestion(session, default_csv_path)
