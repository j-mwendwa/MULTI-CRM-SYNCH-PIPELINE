from __future__ import annotations

import structlog
from fastapi import APIRouter

from src.api.schemas import LeadInbound, LeadResponse
from src.graph.graph import run_pipeline

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["leads"])


@router.post("/leads", response_model=LeadResponse)
async def ingest_lead(lead: LeadInbound) -> LeadResponse:
    logger.info("lead_received", source=lead.source, email=lead.email)
    return await run_pipeline(lead)
