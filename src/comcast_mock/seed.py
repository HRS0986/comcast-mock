from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comcast_mock.models import Category, SubCategory, Ticket

# Reference data mirrors the live Neon schema (integer auto-increment IDs).
# Insertion order reproduces the same integers on a fresh database, so the
# seed is deterministic whether run against Neon or the local SQLite fallback.
CATEGORIES_DATA: list[tuple[int, str, str]] = [
    (
        1,
        "Refund",
        "Issues where a customer is owed money back — from a service credit, an "
        "overpayment, a cancelled order, or a billing correction — and is asking "
        "about the status, amount, or method of that refund",
    ),
    (
        2,
        "Technical Support",
        "Technical problems and application issues",
    ),
    (
        3,
        "Account",
        "Customer account related issues",
    ),
    (
        4,
        "Network",
        "Internet and network related issues",
    ),
    (
        5,
        "Promotions",
        "Issues related to promotional offers — discounts, bundles, or "
        "introductory pricing not applying, expiring, or matching what the "
        "customer was told.",
    ),
]

_SUBCATEGORIES_DATA: list[tuple[int, str, int, str]] = [
    (1, "Invoice Explanation", 2, "Questions about invoice charges"),
    (2, "Payment Issue", 2, "Problems with customer payments"),
    (3, "Unexpected Charge", 2, "Customer does not recognize a charge"),
    (
        4,
        "Local",
        1,
        "Refunds processed to a domestic account or payment method (in-country bank "
        "transfer, local card, local billing address)",
    ),
    (
        5,
        "International",
        1,
        "Refunds involving a payment method, bank account, or billing address outside "
        "the country, which may involve currency conversion, longer processing "
        "times, or cross-border transfer requirements.",
    ),
    (6, "Profile Update", 3, "Customer wants to update account information"),
    (7, "Account Closure", 3, "Customer wants to close their account"),
    (8, "Internet Connection", 4, "Customer cannot connect to the internet"),
    (9, "Slow Internet", 4, "Customer reports slow internet"),
    (
        10,
        "Promo Not Applied",
        5,
        "Customer signed up for or was promised a promotional rate, but it isn't "
        "reflected on the account or bill.",
    ),
    (
        11,
        "Promo Expired / Price Increase",
        5,
        "Customer's promotional period ended and they were moved to standard "
        "pricing, often without expecting it.",
    ),
    (
        12,
        "Promo Eligibility Dispute",
        5,
        "Customer believes they qualify for an offer (new customer deal, loyalty "
        "offer, bundle discount) but the system or agent says they don't.",
    ),
]

_TICKET_DATA: list[tuple[str, str, str | None, int | None, int | None]] = [
    (
        "Internet is down - no sync on cable modem",
        "Arris SB8200 shows no downstream lock; modem offline.",
        4,
        8,
    ),
    (
        "Frequent connection drops every few minutes",
        "Intermittent loss on NODE-4471; high corrected codewords.",
        4,
        9,
    ),
    (
        "Slow speeds - 900 Mbps plan delivering 40 Mbps",
        "Gigabit plan only seeing fraction of expected throughput.",
        4,
        9,
    ),
    (
        "Billing discrepancy - unexpected charge",
        "Customer was charged $25 equipment fee not previously disclosed.",
        2,
        3,
    ),
]

_TICKET_STATUS = ["new", "in_progress", "new", "open"]


def build_categories() -> list[Category]:
    return [Category(id=cid, name=name, description=desc) for cid, name, desc in CATEGORIES_DATA]


def build_subcategories() -> list[SubCategory]:
    return [
        SubCategory(id=sid, name=name, category_id=cat_id, description=desc)
        for sid, name, cat_id, desc in _SUBCATEGORIES_DATA
    ]


def build_tickets() -> list[Ticket]:
    return [
        Ticket(
            title=title,
            description=desc,
            category_id=cat_id,
            sub_category_id=sub_id,
            status=status,
        )
        for (title, desc, cat_id, sub_id), status in zip(_TICKET_DATA, _TICKET_STATUS, strict=True)
    ]


async def seed_database(session: AsyncSession) -> None:
    cat_count = (await session.execute(select(Category.id))).scalars().all()
    if not cat_count:
        session.add_all(build_categories())
    sub_count = (await session.execute(select(SubCategory.id))).scalars().all()
    if not sub_count:
        session.add_all(build_subcategories())
    ticket_count = (await session.execute(select(Ticket.id))).scalars().all()
    if not ticket_count:
        session.add_all(build_tickets())
    await session.commit()
