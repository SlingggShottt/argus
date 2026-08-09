"""Conversational Insight Agent: the only LLM-backed node in the pipeline
(style_guide.md's LLM boundary rule). Takes a user's NL question and uses
LangChain tool-calling so the LLM pulls only the specific structured data
slice it needs (a forecast lookup, the risk list, or recommendations)
instead of every prompt getting the full dataset dumped into it."""

import logging
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.db.models import Forecast, Recommendation, RiskFlag
from app.services.llm_client import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a supply chain analyst assistant. Answer the user's question "
    "using ONLY the tools provided to look up real forecast, risk, and "
    "recommendation data -- never guess or make up numbers. If a tool "
    "returns no data, say so plainly rather than inventing an answer. "
    "Call each tool AT MOST ONCE per question. As soon as a tool returns a "
    "result, use that result to write your final answer in plain text -- "
    "do not call the same tool again with the same or similar arguments."
)

MAX_TOOL_ROUNDS = 4  # hard cap so a confused model can't loop indefinitely


@dataclass
class ConversationalAgentOutput:
    """Typed output per style_guide.md's agent convention."""

    answer: str
    tool_calls_made: int


def _build_tools(db: Session) -> list:
    """Tools are closures over db so each one queries the current session
    without the LLM ever seeing or controlling DB access directly."""

    @tool
    def get_forecast(store_id: int, item_id: int) -> str:
        """Get the demand forecast for a specific store and item."""
        rows = (
            db.query(Forecast)
            .filter_by(store_id=store_id, item_id=item_id)
            .order_by(Forecast.forecast_date)
            .all()
        )
        if not rows:
            return f"No forecast found for store {store_id}, item {item_id}."
        lines = [f"{r.forecast_date}: {r.predicted_sales:.1f} units" for r in rows]
        return f"Forecast for store {store_id}, item {item_id} ({rows[0].horizon_days}-day horizon):\n" + "\n".join(
            lines
        )

    @tool
    def get_risks(risk_type: str = "", severity: str = "") -> str:
        """Get flagged at-risk SKUs. risk_type filters to 'stockout' or
        'anomaly'; severity filters to 'high' or 'medium'. Leave blank for
        all flags."""
        query = db.query(RiskFlag)
        if risk_type:
            query = query.filter_by(risk_type=risk_type)
        if severity:
            query = query.filter_by(severity=severity)
        rows = query.all()
        if not rows:
            return "No matching risk flags found."
        lines = [
            f"store {r.store_id}, item {r.item_id}: {r.risk_type} ({r.severity}) - {r.details}" for r in rows
        ]
        return "\n".join(lines)

    @tool
    def get_recommendations(store_id: int = 0, item_id: int = 0) -> str:
        """Get reorder point/quantity recommendations, optionally filtered
        to a specific store_id and/or item_id (0 means unfiltered)."""
        query = db.query(Recommendation)
        if store_id:
            query = query.filter_by(store_id=store_id)
        if item_id:
            query = query.filter_by(item_id=item_id)
        rows = query.all()
        if not rows:
            return "No matching recommendations found."
        lines = [
            f"store {r.store_id}, item {r.item_id}: reorder_point={r.reorder_point:.1f}, "
            f"reorder_quantity={r.reorder_quantity:.1f}"
            for r in rows
        ]
        return "\n".join(lines)

    return [get_forecast, get_risks, get_recommendations]


def run(db: Session, question: str) -> ConversationalAgentOutput:
    """Single entrypoint, per style_guide.md's agent convention. Runs a
    manual tool-calling loop: ask the LLM, execute whatever tools it
    requests, feed results back, repeat until it answers in plain text."""
    tools = _build_tools(db)
    tools_by_name = {t.name: t for t in tools}
    llm = get_llm().bind_tools(tools)

    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(question)]
    response = llm.invoke(messages)
    messages.append(response)

    tool_calls_made = 0
    rounds = 0
    while response.tool_calls and rounds < MAX_TOOL_ROUNDS:
        for call in response.tool_calls:
            tool_calls_made += 1
            result = tools_by_name[call["name"]].invoke(call["args"])
            logger.info("Conversational agent tool call: %s(%s) -> %.200s", call["name"], call["args"], result)
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        response = llm.invoke(messages)
        messages.append(response)
        rounds += 1

    return ConversationalAgentOutput(answer=response.content, tool_calls_made=tool_calls_made)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        result = run(session, "Which SKUs are at high risk of stockout?")
        print(result.answer)
