"""XGBoost demand forecasting. One global model trained across every
store-item combination (not 500 separate per-SKU models) — a single tree
ensemble that learns shared calendar seasonality generalizes better and is
far simpler to manage than a model per SKU. Pure ML logic only: no DB access,
no config beyond hyperparameters — the agent layer owns orchestration."""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

FEATURE_COLUMNS = [
    "store_id",
    "item_id",
    "year",
    "month",
    "day",
    "day_of_week",
    "day_of_year",
    "week_of_year",
]


def _add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derives date-based features XGBoost can actually learn seasonality
    from — a tree can't infer 'this is a Tuesday in December' from a raw
    date object, it needs that broken out into explicit numeric columns."""
    df = df.copy()
    dt = pd.to_datetime(df["date"])
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month
    df["day"] = dt.dt.day
    df["day_of_week"] = dt.dt.dayofweek
    df["day_of_year"] = dt.dt.dayofyear
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    return df


def mean_absolute_percentage_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    """MAPE: average absolute error as a percentage of the actual value.
    Rows where actual sales are 0 are skipped to avoid dividing by zero —
    a known limitation of MAPE, not something this project works around."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    nonzero = actual != 0
    return float(np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100)


def seasonal_naive_forecast(full_sales_df: pd.DataFrame, holdout_df: pd.DataFrame) -> np.ndarray:
    """Baseline to beat: predicts each holdout day's sales as that same
    store-item's actual sales exactly 7 days earlier (captures weekly
    seasonality with zero modeling). Looks values up from the FULL sales
    history, not just the pre-holdout training slice — day D's lag-7 value
    is always real, already-happened data relative to D, so this uses no
    future information even when the lag lands inside the holdout window."""
    lookup = full_sales_df.set_index(["store_id", "item_id", "date"])["sales"]
    fallback = float(full_sales_df["sales"].mean())

    predictions = []
    for row in holdout_df.itertuples(index=False):
        lag_date = row.date - timedelta(days=7)
        predictions.append(lookup.get((row.store_id, row.item_id, lag_date), fallback))
    return np.array(predictions)


@dataclass
class ForecastModel:
    """Thin wrapper around XGBRegressor with feature engineering baked in —
    callers pass plain (date, store_id, item_id, sales) DataFrames and never
    touch the derived feature columns directly."""

    model: XGBRegressor | None = None
    n_estimators: int = 300
    max_depth: int = 6
    learning_rate: float = 0.05

    def train(self, df: pd.DataFrame) -> None:
        features = _add_calendar_features(df)
        self.model = XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            objective="reg:squarederror",
            random_state=42,
        )
        self.model.fit(features[FEATURE_COLUMNS], features["sales"])

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        features = _add_calendar_features(df)
        predictions = self.model.predict(features[FEATURE_COLUMNS])
        # Demand can't be negative — XGBoost regression has no built-in floor.
        return np.clip(predictions, a_min=0, a_max=None)
