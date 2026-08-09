"""Risk/Anomaly Agent: flags stockout risk (projected demand vs. current
stock, from Forecast + Inventory) and statistically anomalous recent demand
(z-score, rolling-window baseline). Deterministic — no LLM calls, per
style_guide.md's rule that the LLM boundary stays at the Conversational Agent."""

import logging
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Forecast, Inventory, RiskFlag, SalesRecord

logger = logging.getLogger(__name__)


@dataclass
class RiskAgentOutput:
    """Typed output per style_guide.md's agent convention."""

    rows_written: int
    stockout_risk_count: int
    anomaly_count: int


def _load_projected_demand_over_lead_time(db: Session) -> pd.DataFrame:
    """Sums each SKU's predicted sales over the next lead_time_days of its
    forecast — the demand that would need covering before a reorder placed
    today could actually arrive."""
    rows = (
        db.query(Forecast.store_id, Forecast.item_id, Forecast.forecast_date, Forecast.predicted_sales)
        .order_by(Forecast.store_id, Forecast.item_id, Forecast.forecast_date)
        .all()
    )
    df = pd.DataFrame(rows, columns=["store_id", "item_id", "forecast_date", "predicted_sales"])
    if df.empty:
        return pd.DataFrame(columns=["store_id", "item_id", "projected_demand"])

    # head(N) per group relies on rows already being sorted by forecast_date
    # within each store-item (done in the query above) — this grabs each
    # SKU's soonest lead_time_days of forecasted demand, not an arbitrary N.
    nearest_horizon = df.groupby(["store_id", "item_id"]).head(settings.lead_time_days)
    return (
        nearest_horizon.groupby(["store_id", "item_id"])["predicted_sales"]
        .sum()
        .reset_index()
        .rename(columns={"predicted_sales": "projected_demand"})
    )


def _load_inventory(db: Session) -> pd.DataFrame:
    rows = db.query(Inventory.store_id, Inventory.item_id, Inventory.current_stock).all()
    return pd.DataFrame(rows, columns=["store_id", "item_id", "current_stock"])


def _load_sales(db: Session) -> pd.DataFrame:
    rows = db.query(SalesRecord.store_id, SalesRecord.item_id, SalesRecord.date, SalesRecord.sales).all()
    return pd.DataFrame(rows, columns=["store_id", "item_id", "date", "sales"])


def _stockout_risk_flags(demand_df: pd.DataFrame, inventory_df: pd.DataFrame) -> list[dict]:
    merged = demand_df.merge(inventory_df, on=["store_id", "item_id"], how="inner")

    flags = []
    for row in merged.itertuples(index=False):
        if row.current_stock <= 0:
            severity = "high"
            details = (
                f"No stock remaining; projected demand over the next "
                f"{settings.lead_time_days} days is {row.projected_demand:.1f} units."
            )
        else:
            ratio = row.projected_demand / row.current_stock
            if ratio >= 1.0:
                severity = "high"
            elif ratio >= settings.stockout_risk_threshold:
                severity = "medium"
            else:
                continue
            details = (
                f"Projected demand over {settings.lead_time_days}-day lead time "
                f"({row.projected_demand:.1f} units) is {ratio:.0%} of current stock "
                f"({row.current_stock:.1f} units)."
            )

        flags.append(
            {
                "store_id": int(row.store_id),
                "item_id": int(row.item_id),
                "risk_type": "stockout",
                "severity": severity,
                "details": details,
            }
        )
    return flags


def _anomaly_flags(sales_df: pd.DataFrame) -> list[dict]:
    """Compares each SKU's last anomaly_recent_window_days of actual sales
    against a baseline drawn from the anomaly_baseline_window_days right
    before it — not the SKU's entire history, which would bake in yearly
    seasonality (e.g. every December would look like a false 'spike' against
    a 5-year average) and drown out genuine anomalies in seasonal noise."""
    if sales_df.empty:
        return []

    max_date = sales_df["date"].max()
    recent_start = max_date - timedelta(days=settings.anomaly_recent_window_days - 1)
    baseline_end = recent_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=settings.anomaly_baseline_window_days - 1)

    flags = []
    for (store_id, item_id), group in sales_df.groupby(["store_id", "item_id"]):
        baseline = group.loc[(group["date"] >= baseline_start) & (group["date"] <= baseline_end), "sales"]
        recent = group.loc[group["date"] >= recent_start, "sales"]

        if baseline.empty or recent.empty:
            continue

        baseline_mean = baseline.mean()
        baseline_std = baseline.std()
        if pd.isna(baseline_std) or baseline_std == 0:
            continue  # no meaningful variation in the baseline to compare against

        recent_mean = recent.mean()
        z_score = (recent_mean - baseline_mean) / baseline_std
        if abs(z_score) < settings.anomaly_zscore_threshold:
            continue

        direction = "spike" if z_score > 0 else "drop"
        severity = "high" if abs(z_score) >= settings.anomaly_zscore_threshold * 1.5 else "medium"

        flags.append(
            {
                "store_id": int(store_id),
                "item_id": int(item_id),
                "risk_type": "anomaly",
                "severity": severity,
                "details": (
                    f"Recent {settings.anomaly_recent_window_days}-day avg demand "
                    f"({recent_mean:.1f}) is a {direction} of {z_score:.2f} standard "
                    f"deviations from its {settings.anomaly_baseline_window_days}-day "
                    f"baseline average ({baseline_mean:.1f})."
                ),
            }
        )
    return flags


def run(db: Session) -> RiskAgentOutput:
    """Single entrypoint, per style_guide.md's agent convention."""
    demand_df = _load_projected_demand_over_lead_time(db)
    inventory_df = _load_inventory(db)
    sales_df = _load_sales(db)

    stockout_flags = _stockout_risk_flags(demand_df, inventory_df)
    anomaly_flags = _anomaly_flags(sales_df)
    all_flags = stockout_flags + anomaly_flags

    db.query(RiskFlag).delete()
    if all_flags:
        db.bulk_insert_mappings(RiskFlag, all_flags)
    db.commit()
    logger.info(
        "Wrote %d risk flags (%d stockout, %d anomaly)",
        len(all_flags),
        len(stockout_flags),
        len(anomaly_flags),
    )

    return RiskAgentOutput(
        rows_written=len(all_flags),
        stockout_risk_count=len(stockout_flags),
        anomaly_count=len(anomaly_flags),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        result = run(session)
        print(result)
