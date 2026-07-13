from __future__ import annotations

from src.graph.edges import route_api_call
from src.graph.state import PipelineState


def test_route_api_call_done_when_no_failures() -> None:
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
    assert route_api_call(state) == "done"


def test_route_api_call_retry_all() -> None:
    state: PipelineState = {
        "lead": None,
        "enriched_lead": None,
        "hubspot_payload": None,
        "salesforce_payload": None,
        "odoo_payload": None,
        "results": [],
        "errors": [],
        "retry_attempts": {"hubspot": 1, "salesforce": 1, "odoo": 1},
        "max_retries": 5,
        "base_delay": 1.0,
        "failed_providers": ["hubspot", "salesforce", "odoo"],
    }
    assert route_api_call(state) == "retry_all"
