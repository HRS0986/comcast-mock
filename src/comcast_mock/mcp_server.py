"""MCP server exposing the Comcast Kaya CX Triage backend to AI agents via FastMCP."""

from __future__ import annotations

from comcast_mock.main import app
from fastmcp import FastMCP

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