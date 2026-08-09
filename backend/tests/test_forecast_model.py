"""Tests for the XGBoost forecast model wrapper: calendar features, MAPE,
the seasonal-naive baseline, and a train/predict smoke test. The smoke test
checks the pipeline runs and returns sane output — it's not a forecast
quality test, which would need a much larger, realistic dataset."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.models.forecast_model import (
    ForecastModel,
    _add_calendar_features,
    mean_absolute_percentage_error,
    seasonal_naive_forecast,
)


def test_add_calendar_features_known_date():
    df = pd.DataFrame({"date": [date(2017, 12, 31)]})  # a known Sunday

    features = _add_calendar_features(df)

    assert features.loc[0, "year"] == 2017
    assert features.loc[0, "month"] == 12
    assert features.loc[0, "day"] == 31
    assert features.loc[0, "day_of_week"] == 6  # Monday=0 ... Sunday=6
    assert features.loc[0, "day_of_year"] == 365


def test_mape_known_values():
    actual = np.array([100, 200, 50])
    predicted = np.array([110, 180, 50])
    # errors: 10/100=10%, 20/200=10%, 0/50=0% -> mean = 6.6667%

    mape = mean_absolute_percentage_error(actual, predicted)

    assert mape == pytest.approx(6.6667, abs=0.01)


def test_mape_skips_zero_actuals():
    actual = np.array([0, 100])
    predicted = np.array([50, 90])
    # row 0 skipped (actual=0); row 1: |100-90|/100 = 10%

    mape = mean_absolute_percentage_error(actual, predicted)

    assert mape == pytest.approx(10.0)


def test_seasonal_naive_forecast_uses_lag_7():
    full_sales = pd.DataFrame(
        {
            "date": [date(2017, 1, 1), date(2017, 1, 8)],
            "store_id": [1, 1],
            "item_id": [1, 1],
            "sales": [42, 999],  # the holdout row's own value must be ignored
        }
    )
    holdout = pd.DataFrame({"date": [date(2017, 1, 8)], "store_id": [1], "item_id": [1]})

    predictions = seasonal_naive_forecast(full_sales, holdout)

    assert predictions[0] == 42  # value from exactly 7 days earlier


def test_seasonal_naive_forecast_falls_back_when_no_lag_value():
    full_sales = pd.DataFrame(
        {
            "date": [date(2017, 1, 1), date(2017, 1, 2)],
            "store_id": [1, 1],
            "item_id": [1, 1],
            "sales": [10, 100],
        }
    )
    holdout = pd.DataFrame({"date": [date(2017, 6, 1)], "store_id": [1], "item_id": [1]})

    predictions = seasonal_naive_forecast(full_sales, holdout)

    assert predictions[0] == pytest.approx(55.0)  # falls back to overall mean (10+100)/2


def test_forecast_model_train_predict_smoke_test():
    dates = pd.date_range("2017-01-01", periods=60, freq="D").date
    df = pd.DataFrame(
        {
            "date": dates,
            "store_id": [1] * 60,
            "item_id": [1] * 60,
            "sales": [10 + (i % 7) for i in range(60)],
        }
    )

    model = ForecastModel(n_estimators=20, max_depth=3)
    model.train(df)
    predictions = model.predict(df)

    assert len(predictions) == len(df)
    assert (predictions >= 0).all()
