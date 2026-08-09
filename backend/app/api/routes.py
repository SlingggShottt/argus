"""FastAPI routes exposing the deterministic agents' stored output and the
Conversational Agent, per SRS FR-8. Thin layer only -- validates requests,
queries the DB or calls the Conversational Agent, returns JSON. No business
logic here; that lives in the agents."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.conversational_agent import run as run_conversational_agent
from app.api.schemas import (
    ForecastMeta,
    ForecastResponse,
    ForecastRow,
    QueryRequest,
    QueryResponse,
    RecommendationMeta,
    RecommendationResponse,
    RecommendationRow,
    RiskFlagRow,
    RiskMeta,
    RiskResponse,
)
from app.db.models import Forecast, Recommendation, RiskFlag
from app.db.session import get_db

router = APIRouter(prefix="/api")


@router.get("/forecasts/{store_id}/{item_id}", response_model=ForecastResponse)
def get_forecast(store_id: int, item_id: int, db: Session = Depends(get_db)) -> ForecastResponse:
    rows = (
        db.query(Forecast)
        .filter_by(store_id=store_id, item_id=item_id)
        .order_by(Forecast.forecast_date)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No forecast found for store {store_id}, item {item_id}.")
    data = [ForecastRow.model_validate(r) for r in rows]
    return ForecastResponse(data=data, meta=ForecastMeta(store_id=store_id, item_id=item_id, count=len(data)))


@router.get("/risks", response_model=RiskResponse)
def get_risks(
    risk_type: str | None = Query(default=None, description="Filter by 'stockout' or 'anomaly'."),
    severity: str | None = Query(default=None, description="Filter by 'high' or 'medium'."),
    db: Session = Depends(get_db),
) -> RiskResponse:
    query = db.query(RiskFlag)
    if risk_type:
        query = query.filter_by(risk_type=risk_type)
    if severity:
        query = query.filter_by(severity=severity)
    rows = query.all()
    data = [RiskFlagRow.model_validate(r) for r in rows]
    return RiskResponse(data=data, meta=RiskMeta(count=len(data)))


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    store_id: int | None = Query(default=None),
    item_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    query = db.query(Recommendation)
    if store_id is not None:
        query = query.filter_by(store_id=store_id)
    if item_id is not None:
        query = query.filter_by(item_id=item_id)
    rows = query.all()
    data = [RecommendationRow.model_validate(r) for r in rows]
    return RecommendationResponse(data=data, meta=RecommendationMeta(count=len(data)))


@router.post("/query", response_model=QueryResponse)
def post_query(request: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    result = run_conversational_agent(db, request.question)
    return QueryResponse(answer=result.answer, tool_calls_made=result.tool_calls_made)
