from __future__ import annotations

import asyncio
from uuid import uuid4

import structlog

from src.api.schemas import (
    EnrichedLead,
    HubSpotPayload,
    SalesforcePayload,
    OdooPayload,
    ApiResult,
)
from src.clients.hubspot import push_to_hubspot
from src.clients.salesforce import push_to_salesforce
from src.clients.odoo import push_to_odoo
from src.config import settings
from src.core.exceptions import ApiError, RateLimitError
from src.graph.state import PipelineState
from src.llm.client import enrich_lead, analyze_error

logger = structlog.get_logger(__name__)


async def score_and_enrich(state: PipelineState) -> dict:
    lead = state["lead"]

    llm_enrichment = {}
    if settings.llm_enrichment_enabled and settings.anthropic_api_key:
        existing = {
            "email": lead.email,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company": lead.company,
            "role": lead.role,
            "phone": lead.phone,
        }
        llm_enrichment = await enrich_lead(lead.raw_payload, existing)

    first_name = llm_enrichment.get("first_name") or lead.first_name
    last_name = llm_enrichment.get("last_name") or lead.last_name
    company = llm_enrichment.get("company") or lead.company or "Unknown"
    role = llm_enrichment.get("role") or lead.role
    phone = llm_enrichment.get("phone") or lead.phone
    llm_score = llm_enrichment.get("confidence_score")
    notes = llm_enrichment.get("notes", "")

    if llm_score is not None:
        score = float(llm_score)
    else:
        score = 0.8 if lead.email and lead.company else 0.3

    enriched = EnrichedLead(
        lead_id=str(uuid4()),
        email=lead.email,
        first_name=first_name,
        last_name=last_name,
        company=company,
        role=role or "",
        phone=phone or "",
        confidence_score=score,
        enrichment_notes=notes,
        source=lead.source,
    )
    logger.info(
        "lead_enriched",
        lead_id=enriched.lead_id,
        score=score,
        llm_used=bool(llm_enrichment),
    )
    return {"enriched_lead": enriched}


async def format_payloads(state: PipelineState) -> dict:
    lead = state["enriched_lead"]
    hubspot = HubSpotPayload(
        properties={
            "email": lead.email,
            "firstname": lead.first_name,
            "lastname": lead.last_name,
            "company": lead.company,
            "jobtitle": lead.role,
            "phone": lead.phone,
        }
    )
    salesforce = SalesforcePayload(
        Email=lead.email,
        FirstName=lead.first_name,
        LastName=lead.last_name,
        Company=lead.company,
        Title=lead.role,
        Phone=lead.phone,
    )
    odoo = OdooPayload(
        name=f"{lead.first_name} {lead.last_name}".strip() or lead.email,
        contact_name=f"{lead.first_name} {lead.last_name}".strip(),
        email_from=lead.email,
        phone=lead.phone,
        partner_name=lead.company,
        company=lead.company,
        title=lead.role,
    )
    return {
        "hubspot_payload": hubspot,
        "salesforce_payload": salesforce,
        "odoo_payload": odoo,
    }


async def retry_dispatcher(state: PipelineState) -> dict:
    return {}


async def push_hubspot(state: PipelineState) -> dict:
    retry_attempts = state.get("retry_attempts", {})
    attempt = retry_attempts.get("hubspot", 0) + 1
    provider = "hubspot"

    try:
        result = await push_to_hubspot(state["hubspot_payload"])
        result.attempt = attempt
        logger.info("hubspot_success", remote_id=result.remote_id, attempt=attempt)
        return {"results": [result], "retry_attempts": {"hubspot": attempt}}
    except (ApiError, RateLimitError) as exc:
        logger.warning("hubspot_failed", error=str(exc), attempt=attempt)
        err = {"provider": provider, "error": str(exc), "attempt": attempt}
        return {
            "errors": [err],
            "retry_attempts": {"hubspot": attempt},
            "failed_providers": [provider],
        }


async def push_salesforce(state: PipelineState) -> dict:
    retry_attempts = state.get("retry_attempts", {})
    attempt = retry_attempts.get("salesforce", 0) + 1
    provider = "salesforce"

    try:
        result = await push_to_salesforce(state["salesforce_payload"])
        result.attempt = attempt
        logger.info("salesforce_success", remote_id=result.remote_id, attempt=attempt)
        return {"results": [result], "retry_attempts": {"salesforce": attempt}}
    except (ApiError, RateLimitError) as exc:
        logger.warning("salesforce_failed", error=str(exc), attempt=attempt)
        err = {"provider": provider, "error": str(exc), "attempt": attempt}
        return {
            "errors": [err],
            "retry_attempts": {"salesforce": attempt},
            "failed_providers": [provider],
        }


async def push_odoo(state: PipelineState) -> dict:
    retry_attempts = state.get("retry_attempts", {})
    attempt = retry_attempts.get("odoo", 0) + 1
    provider = "odoo"

    try:
        result = await push_to_odoo(state["odoo_payload"])
        result.attempt = attempt
        logger.info("odoo_success", remote_id=result.remote_id, attempt=attempt)
        return {"results": [result], "retry_attempts": {"odoo": attempt}}
    except (ApiError, RateLimitError) as exc:
        logger.warning("odoo_failed", error=str(exc), attempt=attempt)
        err = {"provider": provider, "error": str(exc), "attempt": attempt}
        return {
            "errors": [err],
            "retry_attempts": {"odoo": attempt},
            "failed_providers": [provider],
        }


async def evaluate_errors(state: PipelineState) -> dict:
    failed = list(set(state.get("failed_providers", [])))
    retry_attempts = state.get("retry_attempts", {})
    max_retries = settings.max_retry_attempts

    remaining = []
    for provider in failed:
        attempt = retry_attempts.get(provider, 0)
        if attempt >= max_retries:
            logger.error("max_retries_exhausted", provider=provider, attempt=attempt)
            continue

        should_retry = True
        if settings.llm_error_analysis_enabled and settings.anthropic_api_key:
            error_text = _find_error(state, provider)
            if error_text:
                should_retry = await analyze_error(provider, error_text, attempt)

        if should_retry:
            delay = settings.retry_base_delay_seconds * (2 ** (attempt - 1))
            logger.info(
                "scheduling_retry",
                provider=provider,
                attempt=attempt,
                delay_seconds=delay,
                llm_decision=should_retry,
            )
            await asyncio.sleep(delay)
            remaining.append(provider)
        else:
            logger.info("retry_skipped_llm", provider=provider, attempt=attempt)

    return {"failed_providers": remaining}


def _find_error(state: PipelineState, provider: str) -> str | None:
    for err in state.get("errors", []):
        if err.get("provider") == provider:
            return err.get("error")
    return None
