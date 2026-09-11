import hashlib
import random


def _hash_seed(identifier: str) -> int:
    digest = hashlib.md5(identifier.encode("utf-8")).hexdigest()
    return int(digest, 16)


def _rng(identifier: str) -> random.Random:
    return random.Random(_hash_seed(identifier))


_MODELS = [
    "Arris SB8200",
    "Arris SB6190",
    "Netgear CM1100",
    "Netgear CM1200",
    "Motorola MB8611",
    "Motorola MB7621",
    "TP-Link CR700",
    "Linksys CVA902M",
]

_EVENT_TEMPLATES = [
    ("2024-09-08T10:12:00Z", "T401", "DHCP lease renewed", "info"),
    ("2024-09-08T09:55:00Z", "T502", "Ranging request retries exhausted", "warning"),
    ("2024-09-08T08:30:00Z", "T101", "Cable modem registration completed", "info"),
    ("2024-09-08T07:42:00Z", "T801", "No Ranging Response received", "critical"),
    ("2024-09-08T06:15:00Z", "T202", "Dynamic Host Configuration failed", "warning"),
]


def _is_known_offline(identifier: str) -> bool:
    return identifier.upper() in {"CM-88213"}


def get_device_status(device_id: str) -> dict:
    if device_id.upper() == "CM-88213":
        return {
            "device_id": "CM-88213",
            "online": False,
            "model": "Arris SB8200",
            "uptime_seconds": 0,
        }
    rng = _rng(device_id)
    online = not _is_known_offline(device_id) and rng.random() > 0.15
    uptime = 0 if not online else rng.randint(60, 86400)
    return {
        "device_id": device_id,
        "online": online,
        "model": rng.choice(_MODELS),
        "uptime_seconds": uptime,
        "software_version": f"v{rng.randint(1, 9)}.{rng.randint(0, 9)}.{rng.randint(0, 9)}",
    }


def get_signal_metrics(device_id: str) -> dict:
    if device_id.upper() == "CM-88213":
        return {
            "device_id": "CM-88213",
            "downstream_power_dbmv": [-2.0, 1.0, -1.0, 0.0],
            "upstream_power_dbmv": [45.0, 43.0, 44.0],
            "downstream_snr_db": [38.0, 37.5, 39.0, 38.2],
            "uncorrectable_codewords": 0,
            "corrected_codewords": 0,
        }
    rng = _rng(device_id)
    return {
        "device_id": device_id,
        "downstream_power_dbmv": [round(rng.uniform(-5, 15), 1) for _ in range(4)],
        "upstream_power_dbmv": [round(rng.uniform(35, 55), 1) for _ in range(3)],
        "downstream_snr_db": [round(rng.uniform(30, 42), 1) for _ in range(4)],
        "uncorrectable_codewords": rng.randint(0, 50),
        "corrected_codewords": rng.randint(0, 500),
    }


def get_event_logs(device_id: str, hours: int = 24) -> dict:
    if device_id.upper() == "CM-88213":
        events = [
            {
                "timestamp": "2024-09-08T10:12:00Z",
                "event_code": "T401",
                "message": "DHCP lease renewed",
                "severity": "info",
            },
            {
                "timestamp": "2024-09-08T09:55:00Z",
                "event_code": "T502",
                "message": "Ranging request retries exhausted",
                "severity": "warning",
            },
        ]
        return {
            "device_id": device_id,
            "hours": hours,
            "events": events,
            "event_count": len(events),
        }
    rng = _rng(device_id)
    events = []
    for template in _EVENT_TEMPLATES[: rng.randint(1, 5)]:
        events.append(
            {
                "timestamp": template[0],
                "event_code": template[1],
                "message": template[2],
                "severity": template[3],
            }
        )
    return {"device_id": device_id, "hours": hours, "events": events, "event_count": len(events)}


def check_node_health(node_id: str) -> dict:
    if node_id.upper() == "NODE-4471":
        return {
            "node_id": "NODE-4471",
            "outage_flag": True,
            "impacted_count": 143,
        }
    rng = _rng(node_id)
    outage_flag = rng.random() > 0.7
    impacted = 0
    if outage_flag:
        impacted = rng.randint(1, 500)
    return {
        "node_id": node_id,
        "outage_flag": outage_flag,
        "impacted_count": impacted,
        "utilization_pct": round(rng.uniform(10, 95), 1),
    }


def get_customer_impact(node_id: str) -> dict:
    if node_id.upper() == "NODE-4471":
        return {
            "node_id": "NODE-4471",
            "outage_flag": True,
            "impacted_count": 143,
            "services_affected": ["internet", "voice"],
            "estimated_restore_time": "2024-09-09T02:00:00Z",
        }
    rng = _rng(node_id)
    outage_flag = rng.random() > 0.7
    impacted = 0
    if outage_flag:
        impacted = rng.randint(1, 500)
    return {
        "node_id": node_id,
        "outage_flag": outage_flag,
        "impacted_count": impacted,
        "services_affected": rng.sample(["internet", "voice", "video"], k=rng.randint(1, 3)),
        "estimated_restore_time": None,
    }


def restart_device(device_id: str) -> dict:
    return {
        "device_id": device_id,
        "requires_approval": True,
        "simulated_result": "would_restart_ok",
    }
