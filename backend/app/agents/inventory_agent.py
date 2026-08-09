"""Inventory Optimization Agent: computes a reorder point and reorder
quantity per SKU using EOQ (Economic Order Quantity) and safety-stock
formulas. Reads forecasted demand, not raw historical sales — the
forward-looking estimate is what should actually drive how much to reorder
and when, not what already happened.

The dataset has no cost/price data, so eoq_ordering_cost and
eoq_holding_cost_per_unit are documented, config-tunable assumptions (same
pattern as the inventory synthesis in Phase 1) — not derived values."""

import logging
from dataclasses import dataclass
from math import sqrt

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Forecast, Recommendation

logger = logging.getLogger(__name__)


@dataclass
class InventoryAgentOutput:
    """Typed output per style_guide.md's agent convention."""

    rows_written: int


def _load_forecast_demand_stats(db: Session) -> pd.DataFrame:
    """Per SKU: mean and std of predicted daily demand across the full
    forecast horizon — the forward-looking estimate of typical demand and
    its day-to-day variability, feeding both the EOQ and safety-stock calcs."""
    rows = db.query(Forecast.store_id, Forecast.item_id, Forecast.predicted_sales).all()
    df = pd.DataFrame(rows, columns=["store_id", "item_id", "predicted_sales"])
    if df.empty:
        return pd.DataFrame(columns=["store_id", "item_id", "avg_daily_demand", "demand_std"])

    stats = (
        df.groupby(["store_id", "item_id"])["predicted_sales"]
        .agg(avg_daily_demand="mean", demand_std="std")
        .reset_index()
    )
    # A SKU with only one forecast row (shouldn't happen with a real
    # horizon, but defensive) gives an undefined sample std — treat that as
    # zero variance rather than propagating NaN into every downstream sum.
    stats["demand_std"] = stats["demand_std"].fillna(0.0)
    return stats


def _compute_recommendations(stats: pd.DataFrame) -> list[dict]:
    """reorder_point = expected demand during lead time + safety stock
    (buffer for demand variability during that same window, sized to a
    target service level via service_level_z_score).
    reorder_quantity = EOQ, the order size that minimizes total ordering +
    holding cost for a given annual demand."""
    recommendations = []
    for row in stats.itertuples(index=False):
        safety_stock = settings.service_level_z_score * row.demand_std * sqrt(settings.lead_time_days)
        reorder_point = row.avg_daily_demand * settings.lead_time_days + safety_stock

        annual_demand = row.avg_daily_demand * 365
        eoq = sqrt((2 * annual_demand * settings.eoq_ordering_cost) / settings.eoq_holding_cost_per_unit)

        recommendations.append(
            {
                "store_id": int(row.store_id),
                "item_id": int(row.item_id),
                "reorder_point": float(reorder_point),
                "reorder_quantity": float(eoq),
            }
        )
    return recommendations


def run(db: Session) -> InventoryAgentOutput:
    """Single entrypoint, per style_guide.md's agent convention."""
    stats = _load_forecast_demand_stats(db)
    recommendations = _compute_recommendations(stats)

    db.query(Recommendation).delete()
    if recommendations:
        db.bulk_insert_mappings(Recommendation, recommendations)
    db.commit()
    logger.info("Wrote %d reorder recommendations", len(recommendations))

    return InventoryAgentOutput(rows_written=len(recommendations))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        result = run(session)
        print(result)
