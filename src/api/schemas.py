from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class LeadInbound(BaseModel):
    source: str = Field(..., description="Origin of the lead (web_form, csv_import, etc.)")
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str| None = ""
    role: str| None = ""
    phone: str = ""
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class EnrichedLead(BaseModel):
    lead_id: str
    email: str
    first_name: str
    last_name: str
    company: str
    role: str
    phone: str
    confidence_score: float = 0.0
    enrichment_notes: str = ""
    source: str
    ingested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HubSpotPayload(BaseModel):
    properties: dict[str, str]


class SalesforcePayload(BaseModel):
    attributes: dict[str, str] = {"type": "Lead"}
    Email: str
    FirstName: str = ""
    LastName: str = ""
    Company: str
    Title: str = ""
    Phone: str = ""


class OdooPayload(BaseModel):
    name: str = ""
    contact_name: str = ""
    email_from: str
    phone: str = ""
    partner_name: str = ""
    company: str = ""
    title: str = ""
    description: str = ""
    uid: int = 0
    password: str = ""


class ApiResult(BaseModel):
    provider: str
    success: bool
    status_code: int | None = None
    remote_id: str | None = None
    error: str | None = None
    attempt: int = 0


class LeadResponse(BaseModel):
    lead_id: str
    email: str
    results: list[ApiResult]
    total_attempts: int = 0
