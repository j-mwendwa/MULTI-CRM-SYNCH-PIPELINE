from __future__ import annotations

import operator
from typing import Annotated, Any

from src.api.schemas import (
    ApiResult,
    EnrichedLead,
    HubSpotPayload,
    LeadInbound,
    OdooPayload,
    SalesforcePayload,
)


def _merge_dicts(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    merged = dict(a)
    merged.update(b)
    return merged


class PipelineState(dict[str, Any]):
    lead: LeadInbound | None = None
    enriched_lead: EnrichedLead | None = None
    hubspot_payload: HubSpotPayload | None = None
    salesforce_payload: SalesforcePayload | None = None
    odoo_payload: OdooPayload | None = None
    results: Annotated[list[ApiResult], operator.add] = []
    errors: Annotated[list[dict], operator.add] = []
    retry_attempts: Annotated[dict[str, int], _merge_dicts] = {}
    max_retries: int = 5
    base_delay: float = 1.0
    failed_providers: Annotated[list[str], operator.add] = []
