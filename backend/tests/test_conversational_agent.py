"""Tests for the Conversational Agent: the DB-backed tools directly (no LLM
needed), and the tool-calling loop mechanics via a scripted stub LLM (no
real Groq API call -- keeps tests fast, free, and deterministic)."""

from datetime import date

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents import conversational_agent
from app.db.models import Base, Forecast, Recommendation, RiskFlag


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _tool(db, name):
    tools = conversational_agent._build_tools(db)
    return next(t for t in tools if t.name == name)


# ---- tools, tested directly against a seeded DB ----


def test_get_forecast_returns_formatted_forecast(db_session):
    db_session.add(
        Forecast(store_id=1, item_id=1, forecast_date=date(2018, 1, 1), predicted_sales=12.5, horizon_days=30)
    )
    db_session.commit()

    result = _tool(db_session, "get_forecast").invoke({"store_id": 1, "item_id": 1})

    assert "12.5" in result
    assert "2018-01-01" in result


def test_get_forecast_no_data(db_session):
    result = _tool(db_session, "get_forecast").invoke({"store_id": 9, "item_id": 9})

    assert "No forecast found" in result


def test_get_risks_filters_by_type(db_session):
    db_session.add_all(
        [
            RiskFlag(store_id=1, item_id=1, risk_type="stockout", severity="high", details="thin stock"),
            RiskFlag(store_id=2, item_id=2, risk_type="anomaly", severity="medium", details="demand spike"),
        ]
    )
    db_session.commit()

    all_flags = _tool(db_session, "get_risks").invoke({"risk_type": "", "severity": ""})
    stockout_only = _tool(db_session, "get_risks").invoke({"risk_type": "stockout", "severity": ""})

    assert "stockout" in all_flags and "anomaly" in all_flags
    assert "stockout" in stockout_only and "anomaly" not in stockout_only


def test_get_recommendations_no_data(db_session):
    result = _tool(db_session, "get_recommendations").invoke({"store_id": 0, "item_id": 0})

    assert "No matching recommendations found" in result


def test_get_recommendations_returns_values(db_session):
    db_session.add(Recommendation(store_id=1, item_id=1, reorder_point=78.7, reorder_quantity=427.2))
    db_session.commit()

    result = _tool(db_session, "get_recommendations").invoke({"store_id": 1, "item_id": 0})

    assert "78.7" in result
    assert "427.2" in result


# ---- run() loop mechanics, with a scripted stub LLM (no real API call) ----


class _StubLLM:
    """Minimal stand-in for a LangChain chat model: bind_tools() is a no-op
    (returns self), invoke() pops the next pre-scripted response."""

    def __init__(self, responses):
        self._responses = list(responses)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return self._responses.pop(0)


def test_run_answers_directly_when_no_tool_call_needed(db_session, monkeypatch):
    stub = _StubLLM([AIMessage(content="Hello, how can I help?", tool_calls=[])])
    monkeypatch.setattr(conversational_agent, "get_llm", lambda: stub)

    output = conversational_agent.run(db_session, "hi")

    assert output.answer == "Hello, how can I help?"
    assert output.tool_calls_made == 0


def test_run_executes_tool_call_then_returns_final_answer(db_session, monkeypatch):
    db_session.add(RiskFlag(store_id=1, item_id=1, risk_type="stockout", severity="high", details="thin stock"))
    db_session.commit()

    first = AIMessage(content="", tool_calls=[{"name": "get_risks", "args": {}, "id": "call_1"}])
    final = AIMessage(content="Store 1 item 1 is at high stockout risk.", tool_calls=[])
    stub = _StubLLM([first, final])
    monkeypatch.setattr(conversational_agent, "get_llm", lambda: stub)

    output = conversational_agent.run(db_session, "Which SKUs are at risk?")

    assert output.tool_calls_made == 1
    assert output.answer == "Store 1 item 1 is at high stockout risk."


def test_run_stops_after_max_tool_rounds(db_session, monkeypatch):
    # LLM that never stops calling tools -> loop must not hang forever
    looping_call = AIMessage(content="", tool_calls=[{"name": "get_risks", "args": {}, "id": "call_x"}])
    stub = _StubLLM([looping_call] * (conversational_agent.MAX_TOOL_ROUNDS + 2))
    monkeypatch.setattr(conversational_agent, "get_llm", lambda: stub)

    output = conversational_agent.run(db_session, "loop forever?")

    assert output.tool_calls_made == conversational_agent.MAX_TOOL_ROUNDS
