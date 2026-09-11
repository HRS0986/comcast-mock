# Kaya CX Triage Backend (Comcast Mock)

A mock POC backend for **Kaya CX Triage**, an AI-assisted ticket triage system.

**Kaya** (an external drag-and-drop AI agentic workflow platform) performs all
LLM calls, classification, retrieval ranking, hypothesis generation, and text
generation. This backend is a pure **data + mock-integration layer**: Kaya's
workflow nodes call these HTTP endpoints ("tools") to read/write data and to
query mock device/network systems.

> **Non-negotiable:** this backend never calls an LLM, embedding model, or any
> AI API. Anything requiring AI reasoning belongs in Kaya, not here.

## Tech Stack

| Layer        | Choice                                                                 |
|--------------|------------------------------------------------------------------------|
| Backend      | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn                     |
| Language     | Python 3.13                                                            |
| Database     | PostgreSQL (Neon) via SQLAlchemy 2 async + `asyncpg` / `psycopg`       |
| Local dev DB | SQLite (`aiosqlite`) — zero-setup fallback                             |
| Tooling      | [uv](https://docs.astral.sh/uv/) for dependency/package management, `ruff` for lint+format |

## Project Structure

```
src/comcast_mock/
├── __init__.py            # `comcast-mock` console script -> uvicorn entrypoint
├── config.py              # pydantic-settings (reads .env + PG* env vars)
├── database.py            # async engine/session lifecycle + shared Base
├── models.py              # SQLAlchemy ORM models (strict to the schema)
├── schemas.py             # Pydantic request/response models + error envelope
├── exceptions.py          # JSON error-envelope handlers (NOT_FOUND, ...)
├── mock_data.py           # deterministic, hash-keyed mock device/node data
├── seed.py                # reference data + sample tickets (idempotent)
├── main.py                # FastAPI app, lifespan, CORS, router inclusion
└── routers/
    ├── __init__.py        # shared pagination dependency (limit/offset)
    ├── health.py          # GET /health
    ├── tickets.py         # intake, list, detail, patch
    ├── categories.py      # categories + sub-categories reference data
    ├── tools.py           # 6 mock device/network tool endpoints
    ├── investigations.py  # audit-trail logging of tool invocations
    └── analytics.py       # aggregate counts
```

## Database Schema

Built strictly to the schema (no extra columns):

| Table          | Columns                                                       |
|----------------|---------------------------------------------------------------|
| `categories`   | `id`, `name`, `description`                                   |
| `sub_categories` | `id`, `name`, `category_id` (FK), `description`              |
| `tickets`      | `id`, `title`, `description`, `category_id` (FK), `sub_category_id` (FK), `status` |
| `investigations` | `id`, `ticket_id` (FK), `run_id`, `mcp_tools` (JSONB), `inputs` (JSONB) |

`mcp_tools` and `inputs` are parallel arrays: `mcp_tools[i]` was invoked with
`inputs[i]`. On PostgreSQL they are created as `JSONB`; on the local SQLite
fallback they use the generic `JSON` type.

Tables are created with `Base.metadata.create_all` and seeded automatically on
startup (idempotent — safe to run repeatedly). **No migrations tool is wired up
for the POC; see "Production notes" below.**

## Setup

```bash
# from the project root
uv sync --group dev    # installs runtime + dev (ruff) dependencies
```

### Configuration (`.env`, gitignored)

The backend resolves its database URL from `.env` in this order:

1. **`DATABASE_URL`** — if set, used verbatim (pick your driver:
   `postgresql+asyncpg://...` or `postgresql+psycopg://...`).
2. **Individual `PG*` params** — if `PGHOST/PGUSER/PGPASSWORD/PGDATABASE` are
   set, a `postgresql+asyncpg://` URL is built from them. `PGSSLMODE=require`
   is translated to an encrypted connection for `asyncpg`.
3. **Fallback** — `sqlite+aiosqlite:///comcast_mock.db` (local dev, no setup).

Neon connection details (database → Connection Details → "psql" / environment
variables) can be pasted directly as `PG*` params, e.g.:

```env
PGHOST='ep-xxx.us-east-2.aws.neon.tech'
PGDATABASE='comcast_mock'
PGUSER='neondb_owner'
PGPASSWORD='npg_...'
PGSSLMODE='require'
PGCHANNELBINDING='require'
```

## Running

```bash
uv run uvicorn comcast_mock.main:app --reload   # hot-reload dev server (FastAPI)
# or
comcast-mock                                      # console script (FastAPI)
```

### MCP Server (FastMCP)

All FastAPI endpoints are also exposed as MCP tools via FastMCP:

```bash
uv run python -m comcast_mock.mcp_server
```

MCP server runs on `http://0.0.0.0:8000` (HTTP transport). Kaya agents can call tools directly via the MCP protocol instead of HTTP.

Available MCP tools (mapped from REST endpoints):

| MCP Tool Name | Origin (FastAPI) |
|---------------|------------------|
| `health_check` | `GET /health` |
| `create_ticket` | `POST /tickets/ingest` |
| `list_tickets` | `GET /tickets` |
| `get_ticket` | `GET /tickets/{id}` |
| `update_ticket` | `PATCH /tickets/{id}` |
| `create_investigation` | `POST /investigations` |
| `list_investigations` | `GET /investigations` |
| `get_investigation` | `GET /investigations/{id}` |
| `get_analytics_summary` | `GET /analytics/summary` |
| `list_categories` | `GET /categories` |
| `list_sub_categories` | `GET /categories/{id}/sub-categories` |
| `get_sub_category` | `GET /sub-categories/{id}` |
| `get_device_status` | `GET /tools/device-status/{device_id}` |
| `get_signal_metrics` | `GET /tools/signal-metrics/{device_id}` |
| `get_event_logs` | `GET /tools/event-logs/{device_id}` |
| `check_node_health` | `GET /tools/node-health/{node_id}` |
| `get_customer_impact` | `GET /tools/customer-impact/{node_id}` |
| `restart_device` | `POST /tools/restart-device` |

API base URL: `http://localhost:8000/api/v1` (interactive docs at
`http://localhost:8000/api/v1/docs`).

## API Reference

Common patterns:
- **Error envelope** (all errors):
  ```json
  { "error": { "code": "NOT_FOUND", "message": "Ticket ... not found", "details": {} } }
  ```
- **Pagination** (list endpoints): `?limit=&offset=` →
  `{ "items": [...], "total": N, "limit": 50, "offset": 0 }` (default 50, max 200).

### Health
| Method | Path      | Response |
|--------|-----------|----------|
| GET    | `/health` | `{ "status": "ok", "db": "connected", "mcp_mock": "connected" }` |

### Tickets (`POST /tickets/ingest`, `GET /tickets`, `GET /tickets/{id}`, `PATCH /tickets/{id}`)
- `POST /tickets/ingest` — create a ticket (mock intake standing in for ServiceNow/IOP).
  Body: `{ "title": "...", "description": "...", ["category_id"], ["sub_category_id"] }` → `201`.
- `GET /tickets` — list, filterable by `?status=&category_id=&sub_category_id=`, paginated.
- `GET /tickets/{ticket_id}` — full detail incl. nested `category` + `sub_category`.
- `PATCH /tickets/{ticket_id}` — Kaya writes back classification/status:
  `{ "status": "resolved", "category_id": "cat-1", "sub_category_id": "cat-1.1" }`.

### Categories & Sub-Categories
- `GET /categories` → all categories (static reference data).
- `GET /categories/{category_id}/sub-categories` → sub-categories for a category.
- `GET /sub-categories/{sub_category_id}` → a single sub-category.

Seeded reference data: 10 categories × 5 sub-categories = 50 entries, e.g.
`cat-1` → `Network & Connectivity`; sub-categories `cat-1.1` (Modem Offline) … `cat-1.5`.
Mock ticket data is seeded only under `cat-1.1` and `cat-1.2`.

### Mock Device / Network Tools (read-only, deterministic)
| Tool              | Method | Endpoint                                       |
|-------------------|--------|------------------------------------------------|
| get_device_status | GET    | `/api/v1/tools/device-status/{device_id}`       |
| get_signal_metrics| GET    | `/api/v1/tools/signal-metrics/{device_id}`      |
| get_event_logs    | GET    | `/api/v1/tools/event-logs/{device_id}?hours=24` |
| check_node_health | GET    | `/api/v1/tools/node-health/{node_id}`           |
| get_customer_impact | GET  | `/api/v1/tools/customer-impact/{node_id}`       |
| restart_device    | POST   | `/api/v1/tools/restart-device` (body `{"device_id": "..."}`) → `requires_approval: true` |

Responses are deterministic based on the `device_id`/`node_id` passed in (an MD5
of the identifier seeds a PRNG). The example IDs `CM-88213` and `NODE-4471`
return the exact fixture values from the spec.

### Investigations (`POST /investigations`, `GET /investigations?ticket_id=`, `GET /investigations/{id}`)
Audit trail of which tools Kaya invoked and with what inputs, on a given run.
```jsonc
{ "ticket_id": "tkt-...", "run_id": "run-...", "mcp_tools": ["check_node_health","get_signal_metrics"], "inputs": [{"node_id":"NODE-4471"},{"device_id":"CM-88213"}] }
```
`run_id` is **optional**; if omitted the backend generates `run-<12hex>`.

### Analytics
- `GET /analytics/summary` → `{ total_tickets, by_category, by_sub_category, by_status, total_investigations }` (pure SQL aggregations).

## Kaya Agent → Endpoint mapping

| Kaya Agent        | Calls                                                    |
|-------------------|----------------------------------------------------------|
| Intake            | `POST /tickets/ingest`, `PATCH /tickets/{id}`            |
| Enrichment        | `GET /tools/device-status`, `GET /tools/signal-metrics`, `PATCH /tickets/{id}` |
| Hypothesis        | `GET /tools/event-logs`, `GET /tools/node-health`        |
| MCP Invocation    | all `/tools/*`, logged via `POST /investigations`        |
| Validation        | `GET /tools/customer-impact`, `POST /investigations`     |
| Resolution        | `POST /tools/restart-device` (mock), `POST /investigations` |

## Development

```bash
uv run ruff check src/comcast_mock     # lint
uv run ruff format src/comcast_mock     # format
uv run uvicorn comcast_mock.main:app --reload
```

## Production Notes

- Prefer **`asyncpg`** (default for the `PG*` path) — it runs on the default
  asyncio event loop on all platforms. Use `postgresql+psycopg://…` (set
  `DATABASE_URL`) to honor libpq knobs like `channel_binding`; note that on
  Windows this requires a `SelectorEventLoop`.
- For schema evolution, add **Alembic** migrations against the `Base.metadata`
  in `database.py` (the dependency is already declared). Current startup uses
  `create_all`, which does **not** alter existing tables — point at a fresh
  database for a clean schema.
- The local SQLite fallback does not enforce foreign keys; treat it as a
  convenience for offline iteration only.

## Open Items (see AGENTS.md §13)
1. Does the dashboard need confidence/automation-rate data? (Requires a new
   column on `investigations` — confirmed not added to the schema.)
2. `run_id` ownership — resolved as optional, backend-generated when absent.
