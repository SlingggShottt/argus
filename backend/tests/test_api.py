"""Tests for the FastAPI routes: DB dependency overridden with in-memory
SQLite, and the query endpoint's LLM call stubbed (no real Groq API calls
in the test suite)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import conversational_agent
from app.db.models import Base, Forecast, Recommendation, RiskFlag
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def db_session():
    # FastAPI runs sync route handlers in a worker thread, but SQLite's
    # :memory: DB is connection/thread-scoped by default -- without
    # StaticPool, the route handler's thread would see an empty DB even
    # though this fixture just created tables in it on the test's thread.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_forecast_returns_data(client, db_session):
    db_session.add(
        Forecast(store_id=1, item_id=1, forecast_date=date(2018, 1, 1), predicted_sales=12.5, horizon_days=30)
    )
    db_session.commit()

    response = client.get("/api/forecasts/1/1")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["count"] == 1
    assert body["data"][0]["predicted_sales"] == 12.5


def test_get_forecast_404_when_missing(client):
    response = client.get("/api/forecasts/9/9")

    assert response.status_code == 404


def test_get_risks_filters_by_type(client, db_session):
    db_session.add_all(
        [
            RiskFlag(store_id=1, item_id=1, risk_type="stockout", severity="high", details="thin"),
            RiskFlag(store_id=2, item_id=2, risk_type="anomaly", severity="medium", details="spike"),
        ]
    )
    db_session.commit()

    all_response = client.get("/api/risks")
    filtered_response = client.get("/api/risks", params={"risk_type": "stockout"})

    assert all_response.json()["meta"]["count"] == 2
    assert filtered_response.json()["meta"]["count"] == 1
    assert filtered_response.json()["data"][0]["risk_type"] == "stockout"


def test_get_recommendations_filters_by_store(client, db_session):
    db_session.add_all(
        [
            Recommendation(store_id=1, item_id=1, reorder_point=78.7, reorder_quantity=427.2),
            Recommendation(store_id=2, item_id=2, reorder_point=50.0, reorder_quantity=200.0),
        ]
    )
    db_session.commit()

    response = client.get("/api/recommendations", params={"store_id": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["count"] == 1
    assert body["data"][0]["reorder_quantity"] == 427.2


class _StubLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return self._responses.pop(0)


def test_post_query_returns_grounded_answer(client, db_session, monkeypatch):
    db_session.add(RiskFlag(store_id=1, item_id=1, risk_type="stockout", severity="high", details="thin stock"))
    db_session.commit()

    first = AIMessage(content="", tool_calls=[{"name": "get_risks", "args": {}, "id": "call_1"}])
    final = AIMessage(content="Store 1 item 1 is at risk.", tool_calls=[])
    stub = _StubLLM([first, final])
    monkeypatch.setattr(conversational_agent, "get_llm", lambda: stub)

    response = client.post("/api/query", json={"question": "which SKUs are at risk?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Store 1 item 1 is at risk."
    assert body["tool_calls_made"] == 1
