from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import select

from billing_api import handle_payment_callback
from billing_models import Entitlement, Order, Payment, PremiumPlan, User
from billing_credit_service import PACK_3_CREDITS, PACK_3_TESTS_CODE
from database import SessionLocal, engine


class ConcurrentPaymentCallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if SessionLocal is None or engine is None or engine.dialect.name != "postgresql":
            raise unittest.SkipTest("PostgreSQL DATABASE_URL is required")
        cls.user_id: int
        cls.order_public_id: str
        with SessionLocal() as db:
            plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == PACK_3_TESTS_CODE))
            if plan is None:
                plan = PremiumPlan(
                    code=PACK_3_TESTS_CODE,
                    name_fa="CI pack 3 tests",
                    plan_type="credits",
                    duration_days=None,
                    credits_granted=PACK_3_CREDITS,
                    price_minor=2_490_000,
                    currency="IRR",
                    is_active=True,
                    features={"ci_only": True},
                )
                db.add(plan)
                db.flush()

            user = User(
                public_id=str(uuid4()),
                name="Concurrent Callback Test",
                phone="09" + str(uuid4().int % 1_000_000_000).zfill(9),
                password_hash=None,
                role="user",
                status="active",
            )
            db.add(user)
            db.flush()

            order_public_id = str(uuid4())
            order = Order(
                public_id=order_public_id,
                user_id=user.id,
                plan_id=plan.id,
                amount_minor=plan.price_minor,
                currency=plan.currency,
                status="pending",
            )
            db.add(order)
            db.flush()

            db.add(
                Payment(
                    order_id=order.id,
                    provider="mock",
                    provider_authority="MOCK-AUTH-001",
                    amount_minor=plan.price_minor,
                    currency=plan.currency,
                    status="initiated",
                )
            )
            db.commit()
            cls.user_id = user.id
            cls.order_public_id = order_public_id

    def test_different_concurrent_callback_events_grant_once(self) -> None:
        def callback(event_key: str) -> dict:
            with SessionLocal() as db:
                try:
                    result = handle_payment_callback(
                        db,
                        order_public_id=self.order_public_id,
                        authority="MOCK-AUTH-001",
                        status="OK",
                        provider_name="mock",
                        event_key=event_key,
                        raw_callback={"event_key": event_key},
                    )
                    db.commit()
                    return result
                except Exception:
                    db.rollback()
                    raise

        event_keys = [f"ci-concurrent:{uuid4()}", f"ci-concurrent:{uuid4()}"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(callback, event_keys))

        self.assertEqual([row["verified"] for row in results], [True, True])
        self.assertEqual({row["credits_added"] for row in results}, {PACK_3_CREDITS})

        with SessionLocal() as db:
            order = db.scalar(select(Order).where(Order.public_id == self.order_public_id))
            self.assertIsNotNone(order)

            payment = db.scalar(select(Payment).where(Payment.order_id == order.id))
            self.assertIsNotNone(payment)
            self.assertEqual(payment.status, "verified")

            entitlements = list(
                db.scalars(select(Entitlement).where(Entitlement.order_id == order.id))
            )
            self.assertEqual(len(entitlements), 1)
            self.assertEqual(entitlements[0].credits_granted, PACK_3_CREDITS)
            self.assertEqual(entitlements[0].credits_remaining, PACK_3_CREDITS)

            from billing_models import PaymentEvent

            events = list(
                db.scalars(select(PaymentEvent).where(PaymentEvent.payment_id == payment.id))
            )
            self.assertEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
