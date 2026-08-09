"""LangGraph orchestrator: sequences Forecast -> Risk -> Inventory (each
deterministic agent's own run() does the DB read/write) and combines their
typed outputs into one object. Logs each node's output for explainability
(NFR-2). The Conversational Agent (Phase 6) is the only LLM-backed node and
is not part of this graph yet — it will consume this combined output."""

import logging
from dataclasses import dataclass
from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents import forecast_agent, inventory_agent, risk_agent
from app.agents.forecast_agent import ForecastAgentOutput
from app.agents.inventory_agent import InventoryAgentOutput
from app.agents.risk_agent import RiskAgentOutput

logger = logging.getLogger(__name__)


class PipelineState(TypedDict):
    db: Session
    forecast_output: Optional[ForecastAgentOutput]
    risk_output: Optional[RiskAgentOutput]
    inventory_output: Optional[InventoryAgentOutput]


@dataclass
class OrchestratorOutput:
    """Combined output consumed by the API layer (Phase 7) and, later, the
    Conversational Agent (Phase 6) as grounding context."""

    forecast: ForecastAgentOutput
    risk: RiskAgentOutput
    inventory: InventoryAgentOutput


def _forecast_node(state: PipelineState) -> dict:
    output = forecast_agent.run(state["db"])
    logger.info("Orchestrator: forecast node -> %s", output)
    return {"forecast_output": output}


def _risk_node(state: PipelineState) -> dict:
    output = risk_agent.run(state["db"])
    logger.info("Orchestrator: risk node -> %s", output)
    return {"risk_output": output}


def _inventory_node(state: PipelineState) -> dict:
    output = inventory_agent.run(state["db"])
    logger.info("Orchestrator: inventory node -> %s", output)
    return {"inventory_output": output}


def _build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("forecast", _forecast_node)
    graph.add_node("risk", _risk_node)
    graph.add_node("inventory", _inventory_node)
    graph.add_edge(START, "forecast")
    graph.add_edge("forecast", "risk")
    graph.add_edge("risk", "inventory")
    graph.add_edge("inventory", END)
    return graph.compile()


_GRAPH = _build_graph()


def run(db: Session) -> OrchestratorOutput:
    """Single entrypoint, per style_guide.md's agent convention."""
    result = _GRAPH.invoke({"db": db, "forecast_output": None, "risk_output": None, "inventory_output": None})
    return OrchestratorOutput(
        forecast=result["forecast_output"],
        risk=result["risk_output"],
        inventory=result["inventory_output"],
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        result = run(session)
        print(result)
