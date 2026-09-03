from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import billing_models  # noqa: F401
from models import Base
from billing_models import AdminAuditLog, AuthSession, Entitlement, Order, Payment, PaymentEvent, PremiumPlan, User


class BillingModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/dark_horse_test",
        )
        cls.engine = create_engine(cls.database_url)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def test_relationships_and_foreign_keys(self):
        now = datetime.now(timezone.utc)
        with Session(self.engine) as db:
            user = User(public_id="u-1", name="Test", phone="09120000000")
            plan = PremiumPlan(
                code="premium-30",
                name_fa="پریمیوم ۳۰ روزه",
                duration_days=30,
                credits_granted=0,
                price_minor=250000000,
                currency="IRR",
                features={"reports": True},
            )
            db.add_all([user, plan])
            db.flush()
            order = Order(public_id="o-1", user_id=user.id, plan_id=plan.id, amount_minor=plan.price_minor, currency="IRR")
            db.add(order)
            db.flush()
            payment = Payment(order_id=order.id, provider="sandbox", amount_minor=order.amount_minor, currency="IRR")
            db.add(payment)
            db.flush()
            entitlement = Entitlement(
                user_id=user.id,
                plan_id=plan.id,
                source="payment",
                credits_granted=3,
                credits_remaining=3,
                starts_at=now,
                expires_at=now + timedelta(days=30),
                order_id=order.id,
            )
            db.add(entitlement)
            session = AuthSession(user_id=user.id, token_hash="hash-1", expires_at=now + timedelta(days=1))
            db.add(session)
            db.commit()
            self.assertEqual(order.user.id, user.id)
            self.assertEqual(payment.order.id, order.id)
            self.assertEqual(entitlement.plan.code, plan.code)

    def test_money_uses_integer_minor_units(self):
        with Session(self.engine) as db:
            plan = PremiumPlan(code="p", name_fa="پ", duration_days=1, price_minor=1999999999, currency="IRR", features={})
            db.add(plan)
            db.commit()
            self.assertEqual(db.query(PremiumPlan).one().price_minor, 1999999999)

    def test_payment_event_idempotency_key_unique(self):
        with Session(self.engine) as db:
            user = User(public_id="u-2", name="Test", phone="09121111111")
            plan = PremiumPlan(code="p2", name_fa="پ", duration_days=1, price_minor=1000, currency="IRR", features={})
            db.add_all([user, plan])
            db.flush()
            order = Order(public_id="o-2", user_id=user.id, plan_id=plan.id, amount_minor=1000, currency="IRR")
            db.add(order)
            db.flush()
            payment = Payment(order_id=order.id, provider="sandbox", amount_minor=1000, currency="IRR")
            db.add(payment)
            db.flush()
            db.add(PaymentEvent(payment_id=payment.id, event_type="verify", event_key="provider:abc:verify", payload={"ok": True}))
            db.commit()
            db.add(PaymentEvent(payment_id=payment.id, event_type="verify", event_key="provider:abc:verify", payload={"ok": True}))
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_payment_transaction_partial_unique_allows_multiple_nulls_but_blocks_duplicates(self):
        with Session(self.engine) as db:
            user = User(public_id="u-3", name="Test", phone="09123333333")
            plan = PremiumPlan(code="p3", name_fa="پ", price_minor=1000, currency="IRR", features={})
            db.add_all([user, plan])
            db.flush()
            order1 = Order(public_id="o-3", user_id=user.id, plan_id=plan.id, amount_minor=1000, currency="IRR")
            order2 = Order(public_id="o-4", user_id=user.id, plan_id=plan.id, amount_minor=1000, currency="IRR")
            db.add_all([order1, order2])
            db.flush()
            db.add_all([
                Payment(order_id=order1.id, provider="zarinpal", amount_minor=1000, currency="IRR", provider_transaction_id=None),
                Payment(order_id=order2.id, provider="zarinpal", amount_minor=1000, currency="IRR", provider_transaction_id=None),
            ])
            db.commit()
            db.add(
                Payment(
                    order_id=order2.id,
                    provider="zarinpal",
                    amount_minor=1000,
                    currency="IRR",
                    provider_transaction_id="txn-1",
                )
            )
            db.commit()
            db.add(
                Payment(
                    order_id=order1.id,
                    provider="zarinpal",
                    amount_minor=1000,
                    currency="IRR",
                    provider_transaction_id="txn-1",
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_admin_audit_requires_admin_user_fk(self):
        with Session(self.engine) as db:
            db.add(AdminAuditLog(admin_user_id=999, action="grant", target_type="entitlement", target_id="1", metadata_json={"reason": "test"}))
            with self.assertRaises(IntegrityError):
                db.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
