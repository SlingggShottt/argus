"""Pydantic response/request models for the API layer. Kept separate from
the SQLAlchemy models in db/models.py -- the DB schema and the API contract
are allowed to diverge, and never expose ORM objects directly in responses."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class ForecastRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: int
    item_id: int
    forecast_date: date
    predicted_sales: float
    horizon_days: int


class ForecastMeta(BaseModel):
    store_id: int
    item_id: int
    count: int


class ForecastResponse(BaseModel):
    data: list[ForecastRow]
    meta: ForecastMeta


class RiskFlagRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: int
    item_id: int
    risk_type: str
    severity: str
    details: str


class RiskMeta(BaseModel):
    count: int


class RiskResponse(BaseModel):
    data: list[RiskFlagRow]
    meta: RiskMeta


class RecommendationRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: int
    item_id: int
    reorder_point: float
    reorder_quantity: float


class RecommendationMeta(BaseModel):
    count: int


class RecommendationResponse(BaseModel):
    data: list[RecommendationRow]
    meta: RecommendationMeta


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    tool_calls_made: int
