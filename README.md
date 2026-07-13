# Multi-CRM Ingestion Pipeline

Agentic middleware that ingests leads via FastAPI, enriches them with an LLM, and fans out to HubSpot, Salesforce, and Odoo with a self-healing retry loop.

## Architecture

```
POST /api/v1/leads
       |
  score_and_enrich  ← LLM enrichment (Claude extracts company/role/phone from raw payload)
       |
  format_payloads   ← builds per-CRM payloads (HubSpot / Salesforce / Odoo)
       |
  ┌──┬──┬──┐       ← concurrent fan-out
  │  │  │  │
 HubSpot  Salesforce  Odoo
  │  │  │  │
  └──┴──┴──┘
       |
  evaluate_errors   ← LLM error analysis (should_retry or hard fail?)
       |
  ┌──┐              ← conditional edge
 retry  done
 (exponential backoff: t = base × 2^attempt)
```

### Self-Healing Retry Loop

If a CRM API call fails (429 rate limit, 503 unavailable, network timeout), the graph does **not** crash. Instead:

1. Error is captured with provider, status code, and traceback
2. `evaluate_errors` node checks retry budget per provider
3. **LLM analyzes the error** — decides if retry will help (429/503/timeout = yes, 400/auth = no)
4. If retryable, sleeps `base × 2^attempt` seconds (1s → 2s → 4s → 8s)
5. Routes back to **only the failing provider's** push node — successful calls are never replayed
6. Providers that exhaust their retry budget are logged and dropped silently

## LLM Integration

Two places where Claude (Anthropic) is used:

| Node | Purpose | Input | Output |
|---|---|---|---|
| `score_and_enrich` | Lead enrichment | Raw payload + existing fields | Extracted company/role/phone + confidence score |
| `evaluate_errors` | Smart retry decision | Provider name + error text + attempt number | `should_retry: bool` + reasoning |

Both are **opt-in** — set `ANTHROPIC_API_KEY` or disable individually with `LLM_ENRICHMENT_ENABLED=false` / `LLM_ERROR_ANALYSIS_ENABLED=false`. When the LLM is unavailable, the system falls back to heuristics.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Copy and configure
cp .env.example .env
# Edit .env with your CRM credentials and ANTHROPIC_API_KEY

# Run
make serve              # uvicorn on :8000
# or
docker compose up       # containerized

# Ingest a lead
curl -X POST http://localhost:8000/api/v1/leads \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "web_form",
    "email": "alice@acme.com",
    "first_name": "Alice",
    "company": "Acme Corp",
    "raw_payload": {"utm_source": "linkedin", "message": "Interested in enterprise plan"}
  }'
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| POST | `/api/v1/leads` | Ingest a lead → enrich → push to all CRMs |

### Response

```json
{
  "lead_id": "alice@acme.com",
  "email": "alice@acme.com",
  "results": [
    {"provider": "hubspot", "success": true, "remote_id": "123", "attempt": 1},
    {"provider": "salesforce", "success": true, "remote_id": "001...", "attempt": 1},
    {"provider": "odoo", "success": true, "remote_id": "42", "attempt": 2}
  ],
  "total_attempts": 4
}
```

## Project Structure

```
├── Dockerfile / docker-compose.yml
├── configs/config.yaml          runtime tuning
├── prompts/                     LLM prompt templates
│   ├── enrich_lead_v1.md
│   └── analyze_error_v1.md
├── src/
│   ├── api/main.py              FastAPI app
│   ├── api/routes.py            POST /api/v1/leads
│   ├── api/schemas.py           Pydantic models
│   ├── config.py                Settings + YAML loader
│   ├── clients/
│   │   ├── hubspot.py           async httpx → HubSpot CRM API
│   │   ├── salesforce.py        OAuth2 + async → Salesforce SOAP/REST
│   │   └── odoo.py              JSON-RPC → Odoo crm.lead
│   ├── graph/
│   │   ├── graph.py             StateGraph builder + run_pipeline()
│   │   ├── state.py             PipelineState (TypedDict with reducers)
│   │   ├── nodes.py             All LangGraph nodes
│   │   └── edges.py             Conditional routing (retry/done)
│   └── llm/
│       └── client.py            Anthropic Claude wrapper
└── tests/
```

## Configuration

| Env var | Default | Description |
|---|---|---|
| `HUBSPOT_API_KEY` | — | HubSpot private app token |
| `SALESFORCE_*` | — | Salesforce OAuth credentials |
| `ODOO_*` | — | Odoo database URL + credentials |
| `ANTHROPIC_API_KEY` | — | Claude API key (enables LLM features) |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Model for enrichment + error analysis |
| `MAX_RETRY_ATTEMPTS` | `5` | Max retries per provider |
| `RETRY_BASE_DELAY_SECONDS` | `1.0` | Base delay for exponential backoff |

## Makefile

| Command | Description |
|---|---|
| `make install` | pip install |
| `make dev` | pip install with dev extras |
| `make serve` | uvicorn --reload :8000 |
| `make lint` | ruff + mypy |
| `make test` | pytest |

## Deployment

```bash
docker build -t multi-crm-pipeline .
docker run -p 8000:8000 --env-file .env multi-crm-pipeline
```

Or with Docker Compose:

```bash
docker compose up -d
```
