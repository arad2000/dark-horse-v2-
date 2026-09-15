from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from database import engine, get_db
from main_v2 import app
from billing_models import Entitlement, Order, Payment, PaymentEvent, PremiumPlan, User
from models import Base


class CommercialBillingE2ETests(unittest.TestCase):
    """Validate real auth -> free credit -> sandbox payment -> exact 3 non-expiring credits."""

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

    def test_register_consume_buy_callback_replay_then_exactly_three_paid_tests(self):
        with patch("phone_verification_service._send_kavenegar_otp"), patch("phone_verification_service.secrets.randbelow", return_value=123456):
            register = self.client.post(
                "/api/v1/auth/register",
                json={"name": "E2E User", "phone": "09001112233", "password": "strong-pass-123"},
            )
            self.assertEqual(register.status_code, 200, register.text)
            register_body = register.json()
            self.assertTrue(register_body["otp_required"])
            challenge_id = register_body["challenge_id"]

            # Registration itself must not create an authenticated user/session yet.
            with next(get_db()) as db:
                self.assertIsNone(db.scalar(select(User).where(User.phone == "09001112233")))

            verify = self.client.post(
                "/api/v1/auth/register/verify",
                json={"challenge_id": challenge_id, "code": "123456"},
            )
            self.assertEqual(verify.status_code, 200, verify.text)
            verify_body = verify.json()
            token = verify_body["token"]
            user_id = verify_body["user"]["id"]
            self.assertTrue(token)
            self.assertTrue(verify_body["phone_verified"])
            self.assertEqual(verify_body["quota"], 1)

        headers = {"Authorization": f"Bearer {token}"}

        # The real authenticated account must be usable immediately after OTP verification.
        me = self.client.get("/api/v1/me", headers=headers)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["user"]["id"], user_id)

        free_entitlement = None
        with next(get_db()) as db:
            free_entitlement = db.scalar(
                select(Entitlement).where(
                    Entitlement.user_id == user_id,
                    Entitlement.source == "free",
                )
            )
            self.assertIsNotNone(free_entitlement)
            self.assertEqual(free_entitlement.credits_granted, 1)
            self.assertEqual(free_entitlement.credits_remaining, 1)
            self.assertIsNone(free_entitlement.expires_at)

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
        self.assertEqual(callback.headers["location"], "https://asbe-siah.ir/?payment=success")

        # A gateway retry must not turn 3 credits into 6.
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
        self.assertEqual(replay.headers["location"], "https://asbe-siah.ir/?payment=success")

        quota = self.client.get("/api/v1/me/quota", headers=headers)
        self.assertEqual(quota.status_code, 200, quota.text)
        self.assertEqual(quota.json()["credits_remaining"], 3)

        with next(get_db()) as db:
            paid_entitlement = db.scalar(
                select(Entitlement).where(
                    Entitlement.user_id == user_id,
                    Entitlement.source == "payment",
                    Entitlement.order_id.is_not(None),
                )
            )
            self.assertIsNotNone(paid_entitlement)
            self.assertEqual(paid_entitlement.credits_granted, 3)
            self.assertEqual(paid_entitlement.credits_remaining, 3)
            self.assertIsNone(paid_entitlement.expires_at)

            order = db.scalar(select(Order).where(Order.public_id == purchase_body["order_id"]))
            self.assertIsNotNone(order)
            self.assertEqual(order.status, "paid")
            self.assertIsNotNone(order.paid_at)

        # Consume all three purchased tests: 3 -> 2 -> 1 -> 0.
        expected_remaining = [2, 1, 0]
        for expected in expected_remaining:
            paid_consume = self.client.post("/api/v1/me/consume-test", headers=headers)
            self.assertEqual(paid_consume.status_code, 200, paid_consume.text)
            self.assertEqual(paid_consume.json()["credits_remaining"], expected)

        exhausted = self.client.post("/api/v1/me/consume-test", headers=headers)
        self.assertEqual(exhausted.status_code, 409, exhausted.text)

        # The paid entitlement is depleted, but never expires by time/date.
        with next(get_db()) as db:
            paid_entitlement = db.scalar(
                select(Entitlement).where(
                    Entitlement.user_id == user_id,
                    Entitlement.source == "payment",
                    Entitlement.order_id.is_not(None),
                )
            )
            self.assertIsNotNone(paid_entitlement)
            self.assertEqual(paid_entitlement.credits_remaining, 0)
            self.assertIsNone(paid_entitlement.expires_at)


if __name__ == "__main__":
    unittest.main(verbosity=2)
