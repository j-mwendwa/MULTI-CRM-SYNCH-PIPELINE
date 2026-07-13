from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

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


class PipelineState(TypedDict):
    lead: LeadInbound | None
    enriched_lead: EnrichedLead | None
    hubspot_payload: HubSpotPayload | None
    salesforce_payload: SalesforcePayload | None
    odoo_payload: OdooPayload | None
    results: Annotated[list[ApiResult], operator.add]
    errors: Annotated[list[dict[str, Any]], operator.add]
    retry_attempts: Annotated[dict[str, int], _merge_dicts]
    max_retries: int
    base_delay: float
    failed_providers: Annotated[list[str], operator.add]
