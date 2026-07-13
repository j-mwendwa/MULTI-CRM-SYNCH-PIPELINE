from __future__ import annotations

from src.config import settings
from src.graph.state import PipelineState

PROVIDERS = ["hubspot", "salesforce", "odoo"]


def route_api_call(state: PipelineState) -> str:
    failed = set(state.get("failed_providers", []))
    retry_attempts = state.get("retry_attempts", {})
    max_retries = settings.max_retry_attempts

    alive = [p for p in PROVIDERS if p in failed and retry_attempts.get(p, 0) < max_retries]

    if not alive:
        return "done"
    if len(alive) == 1:
        return f"retry_{alive[0]}"
    if set(alive) == {"hubspot", "salesforce"}:
        return "retry_both"
    return "retry_all"
