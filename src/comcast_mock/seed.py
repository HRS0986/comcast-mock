from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.models import Category, SubCategory, Ticket

CATEGORIES_DATA: list[tuple[str, str, str | None]] = [
    ("cat-1", "Network & Connectivity", "Modem, signal, and node network issues."),
    ("cat-2", "Billing & Account", "Charges, payments, billing disputes, account changes."),
    ("cat-3", "Equipment & Provisioning", "Device replacement, shipment, provisioning."),
    ("cat-4", "Speed & Performance", "Throughput, latency, performance degradation."),
    ("cat-5", "Service Interruption", "Outages, partial service loss, regional issues."),
    ("cat-6", "Installation & New Service", "New installs, transfers, self-install kits."),
    ("cat-7", "Technical Support", "Device, app, and access troubleshooting."),
    ("cat-8", "Security & Privacy", "Security events, privacy, compromised accounts."),
    ("cat-9", "Data Usage & Caps", "Data cap overages, usage, policy questions."),
    ("cat-10", "Feedback & Escalations", "Feedback, escalations, executive relations."),
]

_SUBCATEGORIES_DATA: list[tuple[str, str, str]] = [
    ("cat-1", "cat-1.1", "Modem Offline / No Sync"),
    ("cat-1", "cat-1.2", "Degraded Signal / Intermittent Drop"),
    ("cat-1", "cat-1.3", "Upstream Noise"),
    ("cat-1", "cat-1.4", "Node Outage"),
    ("cat-1", "cat-1.5", "Provisioning Failure"),
    ("cat-2", "cat-2.1", "Unexpected Charges"),
    ("cat-2", "cat-2.2", "Billing Cycle Change"),
    ("cat-2", "cat-2.3", "Payment Not Applied"),
    ("cat-2", "cat-2.4", "Refund Request"),
    ("cat-2", "cat-2.5", "Duplicate Bill"),
    ("cat-3", "cat-3.1", "Equipment Replacement"),
    ("cat-3", "cat-3.2", "Self-Install Kit Issues"),
    ("cat-3", "cat-3.3", "Wrong Equipment Shipped"),
    ("cat-3", "cat-3.4", "DOCSIS Provisioning Error"),
    ("cat-3", "cat-3.5", "Rental Equipment Return"),
    ("cat-4", "cat-4.1", "Low Speed Test Results"),
    ("cat-4", "cat-4.2", "High Latency"),
    ("cat-4", "cat-4.3", "Packet Loss"),
    ("cat-4", "cat-4.4", "WiFi Dropout"),
    ("cat-4", "cat-4.5", "Throttling Concern"),
    ("cat-5", "cat-5.1", "Partial Outage"),
    ("cat-5", "cat-5.2", "Full Service Outage"),
    ("cat-5", "cat-5.3", "Intermittent Regional Outage"),
    ("cat-5", "cat-5.4", "Planned Maintenance Impact"),
    ("cat-5", "cat-5.5", "Scheduled Maintenance"),
    ("cat-6", "cat-6.1", "Missed Appointment"),
    ("cat-6", "cat-6.2", "New Install Failed"),
    ("cat-6", "cat-6.3", "Transfer / Move Request"),
    ("cat-6", "cat-6.4", "Service Activation Delay"),
    ("cat-6", "cat-6.5", "Self-Install Setup Help"),
    ("cat-7", "cat-7.1", "App Login / Portal Issue"),
    ("cat-7", "cat-7.2", "Device Setup Help"),
    ("cat-7", "cat-7.3", "Password Reset"),
    ("cat-7", "cat-7.4", "Channel / Guide Problems"),
    ("cat-7", "cat-7.5", "Email / Xfinity Connect"),
    ("cat-8", "cat-8.1", "Security Breach Report"),
    ("cat-8", "cat-8.2", "Spam / Phishing Concerns"),
    ("cat-8", "cat-8.3", "Malware / Botnet"),
    ("cat-8", "cat-8.4", "Privacy Data Request"),
    ("cat-8", "cat-8.5", "Unauthorized Access"),
    ("cat-9", "cat-9.1", "Data Cap Warning"),
    ("cat-9", "cat-9.2", "Data Cap Overage Charge"),
    ("cat-9", "cat-9.3", "Usage Report Inaccuracy"),
    ("cat-9", "cat-9.4", "Data Cap Exemption Request"),
    ("cat-9", "cat-9.5", "Unlimited Data Upgrade"),
    ("cat-10", "cat-10.1", "General Complaint"),
    ("cat-10", "cat-10.2", "Executive Escalation"),
    ("cat-10", "cat-10.3", "Billing Escalation"),
    ("cat-10", "cat-10.4", "Service Quality Escalation"),
    ("cat-10", "cat-10.5", "Positive Feedback"),
]

_TICKET_DATA: list[tuple[str, str, str | None, str, str]] = [
    (
        "3f2a9c1e-4b8d-4e2a-9c1e-4b8d4e2a9c1e",
        "Internet is down - no sync on cable modem",
        "Arris SB8200 shows no downstream lock; modem offline.",
        "cat-1",
        "cat-1.1",
    ),
    (
        "4a7b2f3c-1d5e-4f3a-8b2c-4a7b2f3c1d5e",
        "Frequent connection drops every few minutes",
        "Intermittent loss on NODE-4471; high corrected codewords.",
        "cat-1",
        "cat-1.2",
    ),
    (
        "5c3d8a7b-9e1f-4a5c-8d7b-5c3d8a7b9e1f",
        "Slow speeds - 900 Mbps plan delivering 40 Mbps",
        "Gigabit plan only seeing fraction of expected throughput.",
        "cat-4",
        "cat-4.1",
    ),
    (
        "6e2a4b8c-1d5f-4a7c-8b2e-6e2a4b8c1d5f",
        "Billing discrepancy - unexpected charge",
        "Customer was charged $25 equipment fee not previously disclosed.",
        "cat-2",
        "cat-2.1",
    ),
]

_TICKET_STATUS = ["new", "in_progress", "new", "open"]


def build_categories() -> list[Category]:
    return [Category(id=cid, name=name, description=desc) for cid, name, desc in CATEGORIES_DATA]


def build_subcategories() -> list[SubCategory]:
    return [
        SubCategory(id=sid, name=name, category_id=cat_id)
        for cat_id, sid, name in _SUBCATEGORIES_DATA
    ]


def build_tickets() -> list[Ticket]:
    return [
        Ticket(
            id=tid,
            title=title,
            description=desc,
            category_id=cat_id,
            sub_category_id=sub_id,
            status=status,
        )
        for (tid, title, desc, cat_id, sub_id), status in zip(
            _TICKET_DATA, _TICKET_STATUS, strict=True
        )
    ]


async def seed_database(session: AsyncSession) -> None:
    cat_count = (await session.execute(select(Category.id))).scalars().all()
    if cat_count:
        return

    session.add_all(build_categories())
    session.add_all(build_subcategories())
    session.add_all(build_tickets())
    await session.commit()
