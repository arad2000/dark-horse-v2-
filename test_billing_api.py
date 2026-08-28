from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from billing_api import create_payment_request, handle_payment_callback
from billing_models import Entitlement, Payment, PremiumPlan, User
from models import Base


class BillingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add_all([
                User(id=1, public_id="u-1", name="Test", phone="09000000000"),
                PremiumPlan(id=1, code="free_1_test", name_fa="رایگان — ۱ تست", plan_type="credits", duration_days=None, credits_granted=1, price_minor=0, currency="IRR", is_active=True, features={"tests": 1, "non_expiring": True}),
                PremiumPlan(id=2, code="pack_3_tests", name_fa="بسته ۳ تست", plan_type="credits", duration_days=None, credits_granted=3, price_minor=2_490_000, currency="IRR", is_active=True, features={"tests": 3, "non_expiring": True}),
            ])
            db.commit()

    def test_mock_end_to_end_grants_exactly_three(self):
        with self.SessionLocal() as db:
            created = create_payment_request(
                db,
                user_id=1,
                callback_url="https://example.test/api/v1/billing/callback",
                provider_name="mock",
            )
            db.commit()
            self.assertEqual(created["amount_rial"], 2_490_000)
            result = handle_payment_callback(
                db,
                order_public_id=created["order_id"],
                authority=created["authority"],
                status="OK",
                provider_name="mock",
                event_key="mock:evt:1",
                raw_callback={"Status": "OK", "Authority": created["authority"]},
            )
            db.commit()
            self.assertTrue(result["verified"])
            self.assertEqual(result["credits_added"], 3)
            self.assertEqual(result["credits_remaining"], 3)
            self.assertEqual(db.query(Entitlement).filter(Entitlement.order_id.isnot(None)).count(), 1)

    def test_cancelled_callback_never_verifies_or_grants(self):
        with self.SessionLocal() as db:
            created = create_payment_request(
                db,
                user_id=1,
                callback_url="https://example.test/api/v1/billing/callback",
                provider_name="mock",
            )
            db.commit()
            result = handle_payment_callback(
                db,
                order_public_id=created["order_id"],
                authority=created["authority"],
                status="NOK",
                provider_name="mock",
                event_key="mock:evt:cancelled",
            )
            db.commit()
            self.assertFalse(result["verified"])
            self.assertEqual(result["credits_added"], 0)
            self.assertEqual(db.query(Entitlement).count(), 0)

    def test_invalid_callback_url_is_rejected(self):
        with self.SessionLocal() as db:
            with self.assertRaises(ValueError):
                create_payment_request(db, user_id=1, callback_url="not-a-url", provider_name="mock")

    def test_provider_is_selected_server_side(self):
        with self.SessionLocal() as db:
            with self.assertRaises(ValueError):
                create_payment_request(
                    db,
                    user_id=1,
                    callback_url="https://example.test/callback",
                    provider_name="client-supplied-unknown",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
