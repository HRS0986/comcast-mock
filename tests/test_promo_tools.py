import hashlib
from datetime import datetime, timedelta, timezone
import unittest

from fastapi.testclient import TestClient

from comcast_mock.database import session_factory
from comcast_mock.main import app
from comcast_mock.models import Customer


class PromoToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.account_number = "ACCT-12345"
        self._upsert_customer(self.account_number, country="United States")

    def _upsert_customer(self, account_number: str, country: str) -> None:
        async def _write() -> None:
            async with session_factory() as session:
                existing = await session.get(Customer, account_number)
                if existing is not None:
                    await session.delete(existing)
                session.add(
                    Customer(
                        id=account_number,
                        full_name="Test Customer",
                        email=f"{account_number.lower().replace('-', '')}@example.com",
                        phone="555-0100",
                        account_number=account_number,
                        country=country,
                        status="active",
                        created_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

        import asyncio

        asyncio.run(_write())

    def test_check_promo_application_unknown_account(self) -> None:
        response = self.client.post(
            "/api/v1/tools/check-promo-application",
            json={"account_number": "NO-SUCH-ACCOUNT"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"account_found": False})

    def test_check_promo_application_valid_account(self) -> None:
        response = self.client.post(
            "/api/v1/tools/check-promo-application",
            json={"account_number": self.account_number},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["account_found"])
        self.assertIn("promo_found", payload)
        self.assertIn("applied", payload)
        self.assertIn("expected_discount_pct", payload)

        digest = hashlib.sha256(self.account_number.encode("utf-8")).hexdigest()
        remainder = int(digest, 16) % 3
        if remainder == 0:
            self.assertTrue(payload["promo_found"])
            self.assertTrue(payload["applied"])
        elif remainder == 1:
            self.assertTrue(payload["promo_found"])
            self.assertFalse(payload["applied"])
        else:
            self.assertFalse(payload["promo_found"])
            self.assertNotIn("applied", payload)

    def test_check_promo_application_missing_account_number(self) -> None:
        response = self.client.post(
            "/api/v1/tools/check-promo-application",
            json={},
        )
        self.assertEqual(response.status_code, 400)

    def test_check_promo_expiry_valid_account(self) -> None:
        response = self.client.post(
            "/api/v1/tools/check-promo-expiry",
            json={"account_number": self.account_number},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["account_found"])
        self.assertIn("promo_start_date", payload)
        self.assertIn("promo_end_date", payload)
        self.assertIn("customer_notified", payload)
        self.assertIn("current_price", payload)
        self.assertIn("standard_price", payload)

        created_at = self._read_customer_created_at(self.account_number)
        promo_start = created_at + timedelta(days=7)
        promo_end = promo_start + timedelta(days=365)
        self.assertEqual(payload["promo_start_date"], promo_start.date().isoformat())
        self.assertEqual(payload["promo_end_date"], promo_end.date().isoformat())

    def _read_customer_created_at(self, account_number: str) -> datetime:
        async def _read() -> Customer | None:
            async with session_factory() as session:
                return await session.get(Customer, account_number)

        import asyncio

        customer = asyncio.run(_read())
        assert customer is not None
        return customer.created_at


if __name__ == "__main__":
    unittest.main()
