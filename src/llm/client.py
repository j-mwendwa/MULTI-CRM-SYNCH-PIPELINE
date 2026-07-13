from __future__ import annotations

import time
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


def _count_tokens(text: str) -> int:
    return len(text) // 4


async def enrich_lead(raw_payload: dict[str, Any], existing: dict[str, str]) -> dict[str, Any]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = (
        "You are a lead enrichment assistant. "
        "Extract structured information from the raw lead payload.\n"
        "Return ONLY valid JSON with these fields:\n"
        "  - company: company name (or null if unclear)\n"
        "  - role: job title / role (or null)\n"
        "  - phone: phone number (or null)\n"
        "  - first_name: first name (or null)\n"
        "  - last_name: last name (or null)\n"
        "  - confidence_score: float 0-1 estimating data quality\n"
        "  - notes: brief rationale for the score"
    )
    user_msg = f"Existing fields: {existing}\nRaw payload: {raw_payload}"

    input_tokens = _count_tokens(system + user_msg)
    start = time.monotonic()

    try:
        resp = await client.messages.create(
            model=settings.llm_model,
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        output_tokens = _count_tokens(resp.content[0].text)
        logger.info(
            "llm_enrich",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=settings.llm_model,
        )
        import json

        parsed = json.loads(resp.content[0].text)
        return parsed
    except Exception as exc:
        logger.warning("llm_enrich_failed", error=str(exc), fallback="heuristic")
        return {}


async def analyze_error(provider: str, error: str, attempt: int) -> bool:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = (
        "You are an error analysis assistant for a CRM sync pipeline.\n"
        "Given an API error, determine if retrying is likely to succeed.\n"
        'Return ONLY valid JSON: {"should_retry": true/false, "reason": "..."}\n'
        "Retry is appropriate for: 429 (rate limit), 503 (unavailable),"
        " timeout, network errors.\n"
        "Retry is NOT appropriate for: 400 (bad request), 401/403 (auth),"
        " 404 (not found), validation errors."
    )
    user_msg = f"Provider: {provider}\nAttempt: {attempt}\nError: {error}"

    try:
        resp = await client.messages.create(
            model=settings.llm_model,
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        import json

        result = json.loads(resp.content[0].text)
        return bool(result.get("should_retry", False))
    except Exception:
        status_code = _extract_status_code(error)
        if status_code:
            return status_code in (429, 503, 502, 504) or status_code >= 500
        timeout_keywords = ("timeout", "timed out", "network", "connection")
        return any(kw in error.lower() for kw in timeout_keywords)


def _extract_status_code(error: str) -> int | None:
    import re

    match = re.search(r"HTTP (\d{3})", error)
    if match:
        return int(match.group(1))
    match = re.search(r"status_code=(\d{3})", error)
    if match:
        return int(match.group(1))
    return None
