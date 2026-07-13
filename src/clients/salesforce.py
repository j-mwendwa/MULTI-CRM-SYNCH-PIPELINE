from __future__ import annotations

import structlog
import httpx

from src.api.schemas import SalesforcePayload, ApiResult
from src.config import settings
from src.core.exceptions import ApiError, RateLimitError

logger = structlog.get_logger(__name__)


async def _get_salesforce_token() -> str:
    url = f"{settings.salesforce_base_url}/services/oauth2/token"
    data = {
        "grant_type": "password",
        "client_id": settings.salesforce_client_id,
        "client_secret": settings.salesforce_client_secret,
        "username": settings.salesforce_username,
        "password": settings.salesforce_password + settings.salesforce_security_token,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, data=data)
        resp.raise_for_status()
        return resp.json()["access_token"]


async def push_to_salesforce(payload: SalesforcePayload) -> ApiResult:
    try:
        token = await _get_salesforce_token()
    except Exception as exc:
        raise ApiError("salesforce", 0, f"Auth failed: {exc}")

    url = f"{settings.salesforce_base_url}/services/data/v62.0/sobjects/Lead"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload.model_dump(exclude_none=True), headers=headers)
            if resp.status_code == 429:
                raise RateLimitError("salesforce", 429, resp.text)
            if resp.status_code >= 400:
                raise ApiError("salesforce", resp.status_code, resp.text)
            data = resp.json()
            return ApiResult(
                provider="salesforce",
                success=True,
                status_code=resp.status_code,
                remote_id=data.get("id"),
            )
        except httpx.HTTPError as exc:
            raise ApiError("salesforce", 0, str(exc))
        except Exception as exc:
            raise ApiError("salesforce", 0, f"Unexpected error: {exc}")
