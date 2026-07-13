from __future__ import annotations

import httpx
import structlog

from src.api.schemas import ApiResult, HubSpotPayload
from src.config import settings
from src.core.exceptions import ApiError, RateLimitError

logger = structlog.get_logger(__name__)


async def push_to_hubspot(payload: HubSpotPayload) -> ApiResult:
    url = f"{settings.hubspot_base_url}/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {settings.hubspot_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload.model_dump(), headers=headers)
            if resp.status_code == 429:
                raise RateLimitError("hubspot", 429, resp.text)
            if resp.status_code >= 400:
                raise ApiError("hubspot", resp.status_code, resp.text)
            data = resp.json()
            return ApiResult(
                provider="hubspot",
                success=True,
                status_code=resp.status_code,
                remote_id=data.get("id"),
            )
        except httpx.HTTPError as exc:
            raise ApiError("hubspot", 0, str(exc))
        except Exception as exc:
            raise ApiError("hubspot", 0, f"Unexpected error: {exc}")
