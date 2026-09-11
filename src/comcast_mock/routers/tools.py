from fastapi import APIRouter
from pydantic import BaseModel

from comcast_mock.mock_data import (
    check_node_health,
    get_customer_impact,
    get_device_status,
    get_event_logs,
    get_signal_metrics,
    restart_device,
)

router = APIRouter()


class RestartRequest(BaseModel):
    device_id: str


@router.get("/device-status/{device_id}")
async def device_status(device_id: str) -> dict:
    return get_device_status(device_id)


@router.get("/signal-metrics/{device_id}")
async def signal_metrics(device_id: str) -> dict:
    return get_signal_metrics(device_id)


@router.get("/event-logs/{device_id}")
async def event_logs(device_id: str, hours: int = 24) -> dict:
    return get_event_logs(device_id, hours)


@router.get("/node-health/{node_id}")
async def node_health(node_id: str) -> dict:
    return check_node_health(node_id)


@router.get("/customer-impact/{node_id}")
async def customer_impact(node_id: str) -> dict:
    return get_customer_impact(node_id)


@router.post("/restart-device")
async def restart_device_endpoint(payload: RestartRequest) -> dict:
    return restart_device(payload.device_id)
