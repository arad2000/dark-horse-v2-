from __future__ import annotations

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from billing_credit_service import (
    FREE_CREDITS,
    PACK_3_CREDITS,
    PACK_3_PRICE_RIAL,
    consume_one_test,
    create_pack_order,
    ensure_free_entitlement,
    initiate_payment,
    verify_and_grant,
)
from billing_models import Entitlement, PaymentEvent, PremiumPlan, User
from models import Base
from payment_providers import MockPaymentProvider


class BillingCreditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/dark_horse_test",
        )
        cls.engine = create_engine(database_url, pool_pre_ping=True)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)
        _ = (Entitlement, PremiumPlan, PaymentEvent)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add_all([
                User(id=1, public_id="user-1", name="Test", phone="09000000000"),
                PremiumPlan(id=1, code="free_1_test", name_fa="رایگان — ۱ تست", plan_type="credits", duration_days=None, credits_granted=1, price_minor=0, currency="IRR", is_active=True, features={"tests": 1, "non_expiring": True}),
                PremiumPlan(id=2, code="pack_3_tests", name_fa="بسته ۳ تست", plan_type="credits", duration_days=None, credits_granted=3, price_minor=PACK_3_PRICE_RIAL, currency="IRR", is_active=True, features={"tests": 3, "non_expiring": True}),
            ])
            db.commit()

    def test_free_entitlement_is_exactly_one_and_non_expiring(self):
        with self.SessionLocal() as db:
            first = ensure_free_entitlement(db, 1)
            db.commit()
            second = ensure_free_entitlement(db, 1)
            db.commit()
            self.assertEqual(first.id, second.id)
            self.assertEqual(first.credits_granted, FREE_CREDITS)
            self.assertEqual(first.credits_remaining, FREE_CREDITS)
            self.assertIsNone(first.expires_at)
            self.assertEqual(db.query(Entitlement).count(), 1)

    def test_paid_pack_grants_exactly_three_after_verification(self):
        provider = MockPaymentProvider()
        with self.SessionLocal() as db:
            order, payment, request = initiate_payment(db, 1, provider, "https://example.test/callback")
            db.commit()
            entitlement = verify_and_grant(db, payment.id, provider, request["authority"], "evt-1")
            db.commit()
            self.assertEqual(order.amount_minor, PACK_3_PRICE_RIAL)
            self.assertEqual(entitlement.credits_granted, PACK_3_CREDITS)
            self.assertEqual(entitlement.credits_remaining, PACK_3_CREDITS)
            self.assertIsNone(entitlement.expires_at)

    def test_duplicate_callback_same_event_does_not_double_grant(self):
        provider = MockPaymentProvider()
        with self.SessionLocal() as db:
            _, payment, request = initiate_payment(db, 1, provider, "https://example.test/callback")
            db.commit()
            first = verify_and_grant(db, payment.id, provider, request["authority"], "evt-duplicate")
            db.commit()
            second = verify_and_grant(db, payment.id, provider, request["authority"], "evt-duplicate")
            db.commit()
            self.assertEqual(first.id, second.id)
            self.assertEqual(db.query(Entitlement).filter(Entitlement.order_id == payment.order_id).count(), 1)
            self.assertEqual(db.query(PaymentEvent).filter(PaymentEvent.event_key == "evt-duplicate").count(), 1)

    def test_duplicate_callback_with_different_event_key_does_not_double_grant(self):
        provider = MockPaymentProvider()
        with self.SessionLocal() as db:
            _, payment, request = initiate_payment(db, 1, provider, "https://example.test/callback")
            db.commit()
            first = verify_and_grant(db, payment.id, provider, request["authority"], "evt-1")
            db.commit()
            second = verify_and_grant(db, payment.id, provider, request["authority"], "evt-2")
            db.commit()
            self.assertEqual(first.id, second.id)
            self.assertEqual(db.query(Entitlement).filter(Entitlement.order_id == payment.order_id).count(), 1)
            self.assertEqual(db.query(PaymentEvent).filter(PaymentEvent.payment_id == payment.id).count(), 1)

    def test_consumption_never_goes_negative(self):
        with self.SessionLocal() as db:
            ensure_free_entitlement(db, 1)
            db.commit()
            consume_one_test(db, 1)
            db.commit()
            with self.assertRaises(ValueError):
                consume_one_test(db, 1)

    def test_plan_price_is_server_side_and_exact(self):
        with self.SessionLocal() as db:
            order = create_pack_order(db, 1, "pack_3_tests")
            self.assertEqual(order.amount_minor, PACK_3_PRICE_RIAL)
            self.assertEqual(order.plan_id, 2)

    def test_failed_verification_does_not_grant_credits(self):
        class Failing(MockPaymentProvider):
            def verify_payment(self, *, amount_rial: int, authority: str) -> dict:
                return {"verified": False, "code": -90}

        provider = Failing()
        with self.SessionLocal() as db:
            _, payment, request = initiate_payment(db, 1, provider, "https://example.test/callback")
            db.commit()
            with self.assertRaises(ValueError):
                verify_and_grant(db, payment.id, provider, request["authority"], "evt-fail")
            db.rollback()
            self.assertEqual(db.query(Entitlement).count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
