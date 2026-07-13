from __future__ import annotations

from src.api.schemas import LeadInbound, EnrichedLead, HubSpotPayload, SalesforcePayload, OdooPayload, ApiResult, LeadResponse


def test_lead_inbound_defaults() -> None:
    lead = LeadInbound(source="web_form", email="a@b.com")
    assert lead.source == "web_form"
    assert lead.email == "a@b.com"
    assert lead.first_name == ""
    assert lead.raw_payload == {}


def test_lead_inbound_full() -> None:
    lead = LeadInbound(
        source="csv_import",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        company="Acme",
        role="Engineer",
        phone="+123456789",
        raw_payload={"utm": "google"},
    )
    assert lead.email == "test@example.com"
    assert lead.company == "Acme"


def test_enriched_lead_defaults() -> None:
    lead = EnrichedLead(
        lead_id="abc-123",
        email="a@b.com",
        first_name="A",
        last_name="B",
        company="C",
        role="Engineer",
        phone="+123",
        source="test",
    )
    assert lead.confidence_score == 0.0
    assert lead.ingested_at is not None


def test_hubspot_payload() -> None:
    p = HubSpotPayload(properties={"email": "a@b.com", "company": "Acme"})
    assert p.properties["email"] == "a@b.com"


def test_salesforce_payload() -> None:
    p = SalesforcePayload(Email="a@b.com", Company="Acme")
    assert p.Email == "a@b.com"
    assert p.attributes["type"] == "Lead"


def test_odoo_payload() -> None:
    p = OdooPayload(email_from="a@b.com", name="John Doe")
    assert p.email_from == "a@b.com"
    assert p.uid == 0


def test_api_result_defaults() -> None:
    r = ApiResult(provider="hubspot", success=True)
    assert r.attempt == 0
    assert r.error is None


def test_lead_response() -> None:
    r = ApiResult(provider="hubspot", success=True, remote_id="123")
    resp = LeadResponse(lead_id="a@b.com", email="a@b.com", results=[r], total_attempts=1)
    assert resp.total_attempts == 1
    assert len(resp.results) == 1
