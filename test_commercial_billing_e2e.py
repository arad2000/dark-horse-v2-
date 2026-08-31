from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import delete

from database import engine, get_db
from main_v2 import app
from billing_models import Entitlement, Order, Payment, PaymentEvent, PremiumPlan, User
from models import Base


class CommercialBillingE2ETests(unittest.TestCase):
    """Validate register -> consume free -> mock payment -> callback -> consume."""

    @classmethod
    def setUpClass(cls):
        if not os.getenv("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL is required for PostgreSQL E2E")
        cls.client = TestClient(app)
        with engine.begin() as connection:
            Base.metadata.create_all(connection)

    def setUp(self):
        with next(get_db()) as db:
            db.execute(delete(PaymentEvent))
            db.execute(delete(Entitlement))
            db.execute(delete(Payment))
            db.execute(delete(Order))
            db.execute(delete(User))
            db.execute(delete(PremiumPlan))
            db.commit()
            db.add_all([
                PremiumPlan(
                    code="free_1_test",
                    name_fa="رایگان — ۱ تست",
                    plan_type="credits",
                    duration_days=None,
                    credits_granted=1,
                    price_minor=0,
                    currency="IRR",
                    is_active=True,
                    features={"tests": 1, "non_expiring": True},
                ),
                PremiumPlan(
                    code="pack_3_tests",
                    name_fa="بسته ۳ تست",
                    plan_type="credits",
                    duration_days=None,
                    credits_granted=3,
                    price_minor=2_490_000,
                    currency="IRR",
                    is_active=True,
                    features={"tests": 3, "non_expiring": True},
                ),
            ])
            db.commit()

    def test_register_consume_buy_callback_replay_consume(self):
        register = self.client.post(
            "/api/v1/auth/register",
            json={"name": "E2E User", "phone": "09001112233", "password": "strong-pass-123"},
        )
        self.assertEqual(register.status_code, 200, register.text)
        token = register.json()["token"]
        self.assertEqual(register.json()["quota"], 1)
        headers = {"Authorization": f"Bearer {token}"}

        consumed_free = self.client.post("/api/v1/me/consume-test", headers=headers)
        self.assertEqual(consumed_free.status_code, 200, consumed_free.text)
        self.assertEqual(consumed_free.json()["credits_remaining"], 0)

        purchase = self.client.post("/api/v1/billing/create-payment", headers=headers)
        self.assertEqual(purchase.status_code, 200, purchase.text)
        purchase_body = purchase.json()
        self.assertEqual(purchase_body["provider"], "mock")
        self.assertEqual(purchase_body["amount_rial"], 2_490_000)
        self.assertEqual(purchase_body["authority"], "MOCK-AUTH-001")

        callback = self.client.get(
            "/api/v1/billing/callback",
            params={
                "order_id": purchase_body["order_id"],
                "Authority": purchase_body["authority"],
                "Status": "OK",
            },
            follow_redirects=False,
        )
        self.assertEqual(callback.status_code, 303, callback.text)
        self.assertEqual(callback.headers["location"], "https://arad2000.github.io/dark-horse-v2-/?payment=success")

        replay = self.client.get(
            "/api/v1/billing/callback",
            params={
                "order_id": purchase_body["order_id"],
                "Authority": purchase_body["authority"],
                "Status": "OK",
            },
            follow_redirects=False,
        )
        self.assertEqual(replay.status_code, 303, replay.text)
        self.assertEqual(replay.headers["location"], "https://arad2000.github.io/dark-horse-v2-/?payment=success")

        quota = self.client.get("/api/v1/me/quota", headers=headers)
        self.assertEqual(quota.status_code, 200, quota.text)
        self.assertEqual(quota.json()["credits_remaining"], 3)

        paid_consume = self.client.post("/api/v1/me/consume-test", headers=headers)
        self.assertEqual(paid_consume.status_code, 200, paid_consume.text)
        self.assertEqual(paid_consume.json()["credits_remaining"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
