from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select

from billing_api import handle_payment_callback
from billing_models import Entitlement, Order, Payment, PremiumPlan, User
from payment_providers import MockPaymentProvider
from billing_credit_service import (
    FREE_CREDITS,
    FREE_PLAN_CODE,
    PACK_3_CREDITS,
    PACK_3_TESTS_CODE,
    ensure_free_entitlement,
)
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

            authority = f"MOCK-AUTH-{uuid4().hex[:16]}"
            transaction_id = f"MOCK-REF-{uuid4().hex[:16]}"
            db.add(
                Payment(
                    order_id=order.id,
                    provider="mock",
                    provider_authority=authority,
                    amount_minor=plan.price_minor,
                    currency=plan.currency,
                    status="initiated",
                )
            )
            db.commit()
            cls.user_id = user.id
            cls.order_public_id = order_public_id
            cls.authority = authority
            cls.transaction_id = transaction_id

    def test_concurrent_free_entitlement_provisioning_is_single(self) -> None:
        with SessionLocal() as db:
            plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == FREE_PLAN_CODE))
            if plan is None:
                plan = PremiumPlan(
                    code=FREE_PLAN_CODE,
                    name_fa="CI free test",
                    plan_type="credits",
                    duration_days=None,
                    credits_granted=FREE_CREDITS,
                    price_minor=0,
                    currency="IRR",
                    is_active=True,
                    features={"ci_only": True},
                )
                db.add(plan)
                db.flush()

            user = User(
                public_id=str(uuid4()),
                name="Concurrent Free Entitlement Test",
                phone="09" + str(uuid4().int % 1_000_000_000).zfill(9),
                password_hash=None,
                role="user",
                status="active",
            )
            db.add(user)
            db.commit()
            user_id = user.id

        def provision() -> int:
            with SessionLocal() as db:
                try:
                    row = ensure_free_entitlement(db, user_id)
                    db.commit()
                    return int(row.id)
                except Exception:
                    db.rollback()
                    raise

        with ThreadPoolExecutor(max_workers=2) as pool:
            entitlement_ids = list(pool.map(lambda _: provision(), range(2)))

        self.assertEqual(entitlement_ids[0], entitlement_ids[1])

        with SessionLocal() as db:
            entitlements = list(
                db.scalars(
                    select(Entitlement).where(
                        Entitlement.user_id == user_id,
                        Entitlement.source == "free",
                    )
                )
            )
            self.assertEqual(len(entitlements), 1)
            self.assertEqual(entitlements[0].credits_granted, FREE_CREDITS)
            self.assertEqual(entitlements[0].credits_remaining, FREE_CREDITS)


    def test_different_concurrent_callback_events_grant_once(self) -> None:
        def callback(event_key: str) -> dict:
            with SessionLocal() as db:
                try:
                    with patch(
                        "billing_api.build_provider",
                        return_value=MockPaymentProvider(
                            authority=self.authority,
                            transaction_id=self.transaction_id,
                        ),
                    ):
                        result = handle_payment_callback(
                            db,
                            order_public_id=self.order_public_id,
                            authority=self.authority,
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
            self.assertEqual(payment.provider_transaction_id, self.transaction_id)

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
