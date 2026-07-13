from __future__ import annotations

import structlog
from langgraph.graph import END, StateGraph

from src.api.schemas import LeadInbound, LeadResponse
from src.graph.edges import route_api_call
from src.graph.nodes import (
    evaluate_errors,
    format_payloads,
    push_hubspot,
    push_odoo,
    push_salesforce,
    retry_dispatcher,
    score_and_enrich,
)
from src.graph.state import PipelineState

logger = structlog.get_logger(__name__)


def build_graph() -> StateGraph:
    workflow = StateGraph(PipelineState)

    workflow.add_node("score_and_enrich", score_and_enrich)
    workflow.add_node("format_payloads", format_payloads)
    workflow.add_node("retry_dispatcher", retry_dispatcher)
    workflow.add_node("push_hubspot", push_hubspot)
    workflow.add_node("push_salesforce", push_salesforce)
    workflow.add_node("push_odoo", push_odoo)
    workflow.add_node("evaluate_errors", evaluate_errors)

    workflow.set_entry_point("score_and_enrich")

    workflow.add_edge("score_and_enrich", "format_payloads")
    workflow.add_edge("format_payloads", "push_hubspot")
    workflow.add_edge("format_payloads", "push_salesforce")
    workflow.add_edge("format_payloads", "push_odoo")
    workflow.add_edge("push_hubspot", "evaluate_errors")
    workflow.add_edge("push_salesforce", "evaluate_errors")
    workflow.add_edge("push_odoo", "evaluate_errors")

    workflow.add_conditional_edges(
        "evaluate_errors",
        route_api_call,
        {
            "retry_hubspot": "push_hubspot",
            "retry_salesforce": "push_salesforce",
            "retry_odoo": "push_odoo",
            "retry_both": "retry_dispatcher",
            "retry_all": "retry_dispatcher",
            "done": END,
        },
    )
    workflow.add_edge("retry_dispatcher", "push_hubspot")
    workflow.add_edge("retry_dispatcher", "push_salesforce")
    workflow.add_edge("retry_dispatcher", "push_odoo")

    return workflow.compile()


async def run_pipeline(lead: LeadInbound) -> LeadResponse:
    app = build_graph()
    initial: PipelineState = {
        "lead": lead,
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

    final = await app.ainvoke(initial)
    results = final.get("results", [])
    retry_attempts = final.get("retry_attempts", {})
    total = sum(retry_attempts.values())

    logger.info("pipeline_complete", results=len(results), total_attempts=total)

    return LeadResponse(
        lead_id=initial["lead"].email,
        email=initial["lead"].email,
        results=results,
        total_attempts=total,
    )
