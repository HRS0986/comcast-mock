# AGENTS.md — Kaya CX Triage POC Backend

This file gives AI coding agents (Claude Code, Cursor, Copilot, etc.) the context needed to build and modify this backend correctly. Read this fully before generating code.

## 1. Project Summary

Mock POC backend for **Comcast Kaya CX Triage** — an AI-assisted ticket triage system. Kaya (an external drag-and-drop AI agentic workflow platform) handles **all LLM calls, classification, retrieval ranking, hypothesis generation, and text generation**. This backend does none of that. It is a pure data + mock-integration layer that Kaya's workflow nodes call over HTTP as "tools."

**Non-negotiable rule: this backend must never call an LLM, embedding model, or any AI API.** If a task seems to require one, stop and flag it — it belongs in Kaya, not here.

## 2. Database Schema

```
categories      (id INTEGER PK, name, description)
sub_categories  (id INTEGER PK, name, category_id INTEGER FK, description)
tickets         (id INTEGER PK, title, description, category_id INTEGER FK, sub_category_id INTEGER FK, status)
investigations  (id INTEGER PK, ticket_id INTEGER FK, run_id UUID, mcp_tools, inputs)
```

- `mcp_tools`: JSONB array of tool names invoked during a run, e.g. `["check_node_health", "get_signal_metrics"]`
- `inputs`: JSONB array, same order as `mcp_tools`, e.g. `[{"node_id": "NODE-4471"}, {"device_id": "CM-88213"}]`

All primary/foreign keys are integers (auto-increment sequences); only
`customers.id` and `investigations.run_id` are UUIDs. Reference data is seeded
to match the live Neon database so the same integers reproduce on a fresh DB.

Build strictly against this schema. Do not add columns (embeddings, `device_id`/`node_id` on tickets, `output`/`confidence` on investigations, a `knowledge_base` table, etc.) without checking with the human first — see Section 9.

## 3. Tech Stack

- **Backend:** FastAPI, running on `:8000`
- **Database:** Neon Postgres
- **MCP/Tools:** Served as plain REST from this same FastAPI backend, not a separate MCP-protocol server (confirm with human if this changes)
- **Frontend (separate repo/process):** Vite + React + TypeScript on `:3000` — not part of this backend's scope
- **Dev environment:** Localhost only for POC. 3 devs, 10-day build.

## 4. API Conventions

- Base URL: `http://localhost:8000/api/v1`
- Content-Type: `application/json`
- Pagination on list endpoints: `?limit=&offset=` (default `limit=50`, max `200`):
```json
{ "items": [ ... ], "total": 137, "limit": 50, "offset": 0 }
```
- Error envelope:
```json
{ "error": { "code": "NOT_FOUND", "message": "Ticket 3f2a... not found", "details": {} } }
```
- Standard HTTP codes: `200`, `201`, `400`, `404`, `422`, `500`.

## 5. Health

`GET /health` → `{ "status": "ok", "db": "connected", "mcp_mock": "connected" }`

## 6. Tickets

Backs the `tickets` table. Kaya's Intake/Enrichment/Classification agents call these.

- `POST /tickets/ingest` — mock intake (stands in for ServiceNow/IOP)
- `GET /tickets` — list/filter (`status`, `category_id`, `sub_category_id`)
- `GET /tickets/{ticket_id}` — full detail
- `PATCH /tickets/{ticket_id}` — Kaya writes back classification/status here

## 7. Categories & Sub-Categories

Static reference data, backs `categories` / `sub_categories`. Seeded to match
the live Neon database: 5 categories (`1` Refund, `2` Technical Support,
`3` Account, `4` Network, `5` Promotions) and 12 sub-categories. Insertion
order reproduces the same integers on a fresh DB. Mock ticket data is seeded
under category `4` (Network), sub-categories `8` (Internet Connection) and
`9` (Slow Internet).

- `GET /categories`
- `GET /categories/{category_id}/sub-categories`
- `GET /sub-categories/{sub_category_id}`

## 8. Mock Device / Network Tools

Stand in for the 8 real Comcast backend systems (ServiceNow, IOP, Provisioning, CRM, Billing, Logging). Not backed by any DB table — deterministic mock data keyed by whatever `device_id`/`node_id` is passed in. All READ except `restart_device`, which is a mock WRITE that always returns `requires_approval: true` (remediation execution is read-only in this POC).

| Tool | Endpoint |
|---|---|
| get_device_status | `GET /tools/device-status/{device_id}` |
| get_signal_metrics | `GET /tools/signal-metrics/{device_id}` |
| get_event_logs | `GET /tools/event-logs/{device_id}?hours=24` |
| check_node_health | `GET /tools/node-health/{node_id}` |
| get_customer_impact | `GET /tools/customer-impact/{node_id}` |
| restart_device | `POST /tools/restart-device` |

Example responses:
```json
GET /tools/device-status/CM-88213
{ "device_id": "CM-88213", "online": false, "model": "Arris SB8200", "uptime_seconds": 0 }

GET /tools/node-health/NODE-4471
{ "node_id": "NODE-4471", "outage_flag": true, "impacted_count": 143 }

POST /tools/restart-device  { "device_id": "CM-88213" }
{ "device_id": "CM-88213", "requires_approval": true, "simulated_result": "would_restart_ok" }
```

`tickets` has no `device_id`/`node_id` column, so Kaya passes these explicitly on every tool call rather than the backend resolving them from the ticket.

## 9. Investigations (audit trail)

Backs the `investigations` table: `id` (integer PK), `ticket_id` (integer FK), `run_id` (UUID), `mcp_tools`, `inputs`. Logs which tools were called and with what inputs on a given run.

- `POST /investigations`
```json
{
  "ticket_id": 7,
  "run_id": "123e4567-e89b-12d3-a456-426614174000",
  "mcp_tools": ["check_node_health", "get_signal_metrics"],
  "inputs": [ { "node_id": "NODE-4471" }, { "device_id": "CM-88213" } ]
}
```
- `GET /investigations?ticket_id=7`
- `GET /investigations/{id}`

## 10. Analytics

`GET /analytics/summary` — pure SQL aggregation, no LLM involvement:
```json
{
  "total_tickets": 30,
  "by_category": { "4": 20, "2": 10 },
  "by_sub_category": { "8": 15, "9": 15 },
  "by_status": { "new": 10, "open": 20 }
}
```
Only aggregate what the schema actually supports (ticket counts by category/sub-category/status). Don't fabricate confidence or automation-rate figures — those require data this schema doesn't store; raise it with the human if the dashboard needs them.

## 11. Endpoint-to-Kaya-Agent Mapping

| Kaya Agent | Calls |
|---|---|
| Intake | `POST /tickets/ingest`, `PATCH /tickets/{id}` |
| Enrichment | `GET /tools/device-status`, `GET /tools/signal-metrics`, `PATCH /tickets/{id}` |
| Knowledge Retrieval | handled entirely inside Kaya (no backend endpoint) |
| Hypothesis | `GET /tools/event-logs`, `GET /tools/node-health` |
| MCP Invocation | all `/tools/*` endpoints, logged via `POST /investigations` |
| Validation | `GET /tools/customer-impact`, `POST /investigations` |
| Resolution | `POST /tools/restart-device` (mock), `POST /investigations` |

## 12. Ground Rules for Coding Agents Working on This Repo

1. **Never add an LLM/embedding API call** anywhere in this backend, even to "help" with classification or search relevance — that logic belongs in Kaya.
2. **Build strictly against the schema in Section 2.** Don't add columns or tables to make a feature work — surface the gap and ask instead (see Section 13).
3. Mock tool endpoints (Section 8) are stateless and safe to build immediately.
4. Keep the error envelope and pagination shape (Section 4) consistent across every endpoint you add.
5. This is a localhost POC for a 3-dev, 10-day build — favor simple, readable FastAPI code over premature abstraction (no need for repository patterns, DI containers, etc. at this scale).

## 13. Open Items to Resolve With the Human

1. Does the dashboard need confidence/automation-rate data? If so, `investigations` will need an additional column — confirm before adding one.
2. `run_id` is a UUID column (matches the live Neon schema). It is optional: if omitted the backend generates a random UUID. Callers (Kaya) may pass a UUID string, but must not pass a `run-…`-style string — that would fail the Postgres `uuid` type check.
