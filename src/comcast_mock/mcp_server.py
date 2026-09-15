"""MCP server exposing the Comcast Kaya CX Triage backend to AI agents via FastMCP."""

from __future__ import annotations

from fastmcp import FastMCP

from comcast_mock import database
from comcast_mock.main import app

# FastMCP drives the FastAPI app in-process via httpx2.ASGITransport, which calls
# the ASGI app directly and therefore never triggers the FastAPI ``lifespan``
# startup hook. That hook is what calls ``database.init_engine()``. Without it,
# every endpoint that uses ``get_session`` raises
# ``RuntimeError: Database engine has not been initialized``. Initialize the
# engine here so the MCP server shares the same DB state as the FastAPI server.
database.init_engine()

MCP_NAMES = {
    "health": "health_check",
    "ingest_ticket": "create_ticket",
    "list_tickets": "list_tickets",
    "get_ticket": "get_ticket",
    "update_ticket": "update_ticket",
    "create_investigation": "create_investigation",
    "list_investigations": "list_investigations",
    "get_investigation": "get_investigation",
    "analytics_summary": "get_analytics_summary",
    "list_categories": "list_categories",
    "list_sub_categories": "list_sub_categories",
    "get_sub_category": "get_sub_category",
    "device_status": "get_device_status",
    "signal_metrics": "get_signal_metrics",
    "event_logs": "get_event_logs",
    "node_health": "check_node_health",
    "customer_impact": "get_customer_impact",
    "restart_device_endpoint": "restart_device",
}

mcp = FastMCP.from_fastapi(
    app=app,
    name="kaya-cx-triage-mock",
    mcp_names=MCP_NAMES,
    tags={"tickets", "categories", "investigations", "analytics", "tools"},
)


def main() -> None:
    mcp.run(transport="http", host="0.0.0.0", port=8002)


if __name__ == "__main__":
    main()
