from __future__ import annotations

import structlog
import httpx

from src.api.schemas import OdooPayload, ApiResult
from src.config import settings
from src.core.exceptions import ApiError, RateLimitError

logger = structlog.get_logger(__name__)


def _prepare_xmlrpc_payload(payload: OdooPayload) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                settings.odoo_database,
                payload.uid,
                payload.password,
                "crm.lead",
                "create",
                [
                    {
                        "name": payload.name,
                        "contact_name": payload.contact_name,
                        "email_from": payload.email_from,
                        "phone": payload.phone,
                        "partner_name": payload.partner_name or payload.company,
                        "title": payload.title,
                        "description": payload.description or "",
                    }
                ],
            ],
        },
        "id": 1,
    }


async def _odoo_authenticate() -> tuple[int, str]:
    url = f"{settings.odoo_base_url}/jsonrpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "login",
            "args": [
                settings.odoo_database,
                settings.odoo_username,
                settings.odoo_password,
            ],
        },
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(url, json=payload)
        except Exception as exc:
            raise ApiError("odoo", 0, f"Auth connection failed: {exc}")
        data = resp.json()
        uid = data.get("result")
        if not uid or not isinstance(uid, int):
            raise ApiError("odoo", resp.status_code, f"Auth failed: {data}")
        return uid, settings.odoo_password


async def push_to_odoo(payload: OdooPayload) -> ApiResult:
    uid, password = await _odoo_authenticate()
    p = payload.model_copy(update={"uid": uid, "password": password})
    url = f"{settings.odoo_base_url}/jsonrpc"
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            body = _prepare_xmlrpc_payload(p)
            resp = await client.post(url, json=body, headers=headers)
            result = resp.json()

            err = result.get("error")
            if err:
                code = err.get("code", 0)
                msg = err.get("message", str(err))
                if code == 429:
                    raise RateLimitError("odoo", 429, msg)
                raise ApiError("odoo", code, msg)

            if isinstance(result.get("result"), int):
                return ApiResult(
                    provider="odoo",
                    success=True,
                    status_code=resp.status_code,
                    remote_id=str(result["result"]),
                )
            raise ApiError("odoo", 0, f"Unexpected response: {result}")

        except httpx.HTTPError as exc:
            raise ApiError("odoo", 0, str(exc))
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError("odoo", 0, f"Unexpected error: {exc}")
