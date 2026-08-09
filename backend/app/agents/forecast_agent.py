"""Demand Forecast Agent: trains the global XGBoost model on historical
sales, evaluates it against a seasonal-naive baseline (SRS FR-2.3), and
writes a forecast for the configured horizon to the forecasts table.
Deterministic — no LLM calls, per style_guide.md's rule that the LLM
boundary stays strictly at the Conversational Agent."""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Forecast, SalesRecord
from app.models.forecast_model import (
    ForecastModel,
    mean_absolute_percentage_error,
    seasonal_naive_forecast,
)

logger = logging.getLogger(__name__)


@dataclass
class ForecastAgentOutput:
    """Typed output per style_guide.md's agent convention — the orchestrator
    (Phase 5) and API layer (Phase 7) both consume this directly."""

    rows_written: int
    horizon_days: int
    xgboost_mape: float
    naive_mape: float


def _load_sales(db: Session) -> pd.DataFrame:
    rows = (
        db.query(SalesRecord.date, SalesRecord.store_id, SalesRecord.item_id, SalesRecord.sales)
        .all()
    )
    return pd.DataFrame(rows, columns=["date", "store_id", "item_id", "sales"])


def _future_feature_rows(sku_pairs: pd.DataFrame, start_date: date, horizon_days: int) -> pd.DataFrame:
    """One row per (store, item, future date) for the forecast horizon —
    XGBoost needs an actual feature row to predict against, it can't
    extrapolate forward on its own the way an ARIMA-style model would."""
    future_dates = [start_date + timedelta(days=i) for i in range(1, horizon_days + 1)]
    rows = [
        {"store_id": store_id, "item_id": item_id, "date": future_date}
        for store_id, item_id in sku_pairs.itertuples(index=False)
        for future_date in future_dates
    ]
    return pd.DataFrame(rows)


def run(db: Session) -> ForecastAgentOutput:
    """Single entrypoint, per style_guide.md's 'every agent exposes a single
    clear entrypoint function with typed input/output' convention."""
    sales = _load_sales(db)
    max_date = sales["date"].max()

    # Temporal holdout: train on everything before the last horizon_days,
    # evaluate on those last days. A random shuffle-split would leak future
    # information into training — wrong for time series.
    holdout_start = max_date - timedelta(days=settings.forecast_horizon_days - 1)
    train_df = sales[sales["date"] < holdout_start]
    holdout_df = sales[sales["date"] >= holdout_start]

    model = ForecastModel(
        n_estimators=settings.forecast_n_estimators,
        max_depth=settings.forecast_max_depth,
        learning_rate=settings.forecast_learning_rate,
    )
    model.train(train_df)

    xgboost_predictions = model.predict(holdout_df)
    xgboost_mape = mean_absolute_percentage_error(holdout_df["sales"].to_numpy(), xgboost_predictions)

    naive_predictions = seasonal_naive_forecast(sales, holdout_df)
    naive_mape = mean_absolute_percentage_error(holdout_df["sales"].to_numpy(), naive_predictions)

    logger.info("XGBoost MAPE: %.2f%% | Seasonal-naive MAPE: %.2f%%", xgboost_mape, naive_mape)

    # Retrain on the full dataset (including the former holdout window)
    # before forecasting real future dates — no reason to withhold real,
    # already-happened data from the production forecast once evaluation
    # against the baseline is done.
    model.train(sales)

    sku_pairs = sales[["store_id", "item_id"]].drop_duplicates()
    future_df = _future_feature_rows(sku_pairs, max_date, settings.forecast_horizon_days)
    future_df["predicted_sales"] = model.predict(future_df)

    db.query(Forecast).delete()
    db.bulk_insert_mappings(
        Forecast,
        [
            {
                "store_id": int(row.store_id),
                "item_id": int(row.item_id),
                "forecast_date": row.date,
                "predicted_sales": float(row.predicted_sales),
                "horizon_days": settings.forecast_horizon_days,
            }
            for row in future_df.itertuples(index=False)
        ],
    )
    db.commit()
    logger.info("Wrote %d forecast rows", len(future_df))

    return ForecastAgentOutput(
        rows_written=len(future_df),
        horizon_days=settings.forecast_horizon_days,
        xgboost_mape=xgboost_mape,
        naive_mape=naive_mape,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        result = run(session)
        print(result)
