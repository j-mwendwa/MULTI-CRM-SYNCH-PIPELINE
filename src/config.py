from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    hubspot_api_key: str = ""
    hubspot_base_url: str = "https://api.hubapi.com"

    salesforce_client_id: str = ""
    salesforce_client_secret: str = ""
    salesforce_username: str = ""
    salesforce_password: str = ""
    salesforce_security_token: str = ""
    salesforce_base_url: str = ""

    odoo_base_url: str = ""
    odoo_database: str = ""
    odoo_username: str = ""
    odoo_password: str = ""

    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_enrichment_enabled: bool = True
    llm_error_analysis_enabled: bool = True

    log_level: str = "INFO"
    app_env: str = "dev"

    max_retry_attempts: int = 5
    retry_base_delay_seconds: float = 1.0

    model_config = {"env_file": ".env", "extra": "ignore"}


def _load_config_yaml() -> dict:
    path = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    if path.exists():
        with open(path) as f:
            return dict(yaml.safe_load(f) or {})
    return {}


settings = Settings()
cfg = _load_config_yaml()
