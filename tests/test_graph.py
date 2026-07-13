from __future__ import annotations

from src.graph.graph import build_graph
from src.graph.state import PipelineState
from src.api.schemas import LeadInbound


def test_graph_compiles() -> None:
    g = build_graph()
    assert g is not None


def test_graph_initial_state() -> None:
    state: PipelineState = {
        "lead": None,
        "enriched_lead": None,
        "hubspot_payload": None,
        "salesforce_payload": None,
        "odoo_payload": None,
        "results": [],
        "errors": [],
        "retry_attempts": {},
        "max_retries": 5,
        "base_delay": 1.0,
        "failed_providers": [],
    }
    assert state["max_retries"] == 5
    assert state["results"] == []
