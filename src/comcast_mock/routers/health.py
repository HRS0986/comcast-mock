from fastapi import APIRouter

from comcast_mock import database

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok" if database.db_connected else "degraded",
        "db": "connected" if database.db_connected else "disconnected",
        "mcp_mock": "connected",
    }
