"""SQLAlchemy table definitions. One class per table, matching the tables
each stage of the pipeline reads from / writes to (see docs/design_architecture.md
Data Flow section): raw sales -> inventory snapshot -> forecasts -> risk flags
-> recommendations."""

from datetime import date, datetime

from sqlalchemy import Float, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SalesRecord(Base):
    """Raw historical sales, one row per store-item-day. Loaded directly from
    the Kaggle CSV by the ingestion service, never written to by an agent."""

    __tablename__ = "sales_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    store_id: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[int] = mapped_column(Integer)
    sales: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("date", "store_id", "item_id", name="uq_sales_record"),
        Index("ix_sales_store_item_date", "store_id", "item_id", "date"),
    )


class Inventory(Base):
    """Synthesized current-stock snapshot per store-item, since the source
    dataset has no real inventory field. See context.md for the exact
    synthesis formula and assumptions. One row per store-item — re-running
    ingestion overwrites the existing snapshot rather than appending."""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[int] = mapped_column(Integer)
    avg_daily_demand: Mapped[float] = mapped_column(Float)
    current_stock: Mapped[float] = mapped_column(Float)
    as_of_date: Mapped[date]
    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (UniqueConstraint("store_id", "item_id", name="uq_inventory_sku"),)


class Forecast(Base):
    """Forecast Agent output: predicted demand for a future date per
    store-item. horizon_days records which horizon config produced this row,
    useful if the horizon setting changes between runs."""

    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[int] = mapped_column(Integer)
    forecast_date: Mapped[date]
    predicted_sales: Mapped[float] = mapped_column(Float)
    horizon_days: Mapped[int] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        Index("ix_forecast_store_item_date", "store_id", "item_id", "forecast_date"),
    )


class RiskFlag(Base):
    """Risk/Anomaly Agent output. risk_type distinguishes a stockout-risk row
    (forecasted demand over lead time exceeds current stock) from an
    anomaly row (statistically unusual demand)."""

    __tablename__ = "risk_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[int] = mapped_column(Integer)
    risk_type: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(10))
    details: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (Index("ix_risk_store_item", "store_id", "item_id"),)


class Recommendation(Base):
    """Inventory Optimization Agent output: reorder point and quantity per
    store-item, computed from forecast + risk output via EOQ/safety-stock
    formulas."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[int] = mapped_column(Integer)
    reorder_point: Mapped[float] = mapped_column(Float)
    reorder_quantity: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (Index("ix_recommendation_store_item", "store_id", "item_id"),)
