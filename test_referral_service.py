from __future__ import annotations

import os
import re
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from billing_api import create_payment_request, handle_payment_callback
from billing_models import (
    AdminAuditLog,
    Entitlement,
    Order,
    PremiumPlan,
    ReferralCode,
    User,
)
from models import Base
from referral_service import (
    create_referral_code,
    get_referral_report,
    set_user_referral_code,
)


class ReferralServiceTests(unittest.TestCase):
    """Referral attribution and paid-order reporting use disposable PostgreSQL."""

    @classmethod
    def setUpClass(cls):
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise unittest.SkipTest("DATABASE_URL is required for referral service tests")
        cls.engine = create_engine(database_url, future=True)
        cls.SessionLocal = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            admin = User(
                public_id="ref-admin",
                name="Manager",
                phone="09000000001",
                role="admin",
                status="active",
            )
            support = User(
                public_id="ref-support",
                name="Support",
                phone="09000000002",
                role="support",
                status="active",
            )
            customer = User(
                public_id="ref-customer",
                name="Customer",
                phone="09000000003",
                role="user",
                status="active",
            )
            plan = PremiumPlan(
                code="pack_3_tests",
                name_fa="Three tests",
                plan_type="credits",
                duration_days=None,
                credits_granted=3,
                price_minor=2_490_000,
                currency="IRR",
                is_active=True,
                features={"tests": 3},
            )
            db.add_all([admin, support, customer, plan])
            db.commit()

    def _ids(self, db):
        admin = db.scalar(select(User).where(User.role == "admin"))
        support = db.scalar(select(User).where(User.role == "support"))
        customer = db.scalar(select(User).where(User.role == "user"))
        return admin, support, customer

    def test_manager_only_code_creation_and_random_code(self):
        with self.SessionLocal() as db:
            admin, support, customer = self._ids(db)
            generated = create_referral_code(db, admin, label="Manager generated")
            self.assertRegex(generated.code, re.compile(r"^[A-Z0-9]{10}$"))
            self.assertEqual(generated.created_by_user_id, admin.id)
            self.assertEqual(db.query(AdminAuditLog).count(), 1)
            with self.assertRaises(PermissionError):
                create_referral_code(db, support, label="Support must not create")
            with self.assertRaises(PermissionError):
                create_referral_code(db, customer, label="Customer must not create")

    def test_valid_code_is_snapshotted_once_and_locked_after_first_payment(self):
        with self.SessionLocal() as db:
            admin, support, customer = self._ids(db)
            code = create_referral_code(db, admin, label="Winter campaign", code="SAVE2026")
            revised_code = create_referral_code(db, admin, label="Final campaign", code="FINAL2026")
            db.flush()
            result = set_user_referral_code(db, user_id=customer.id, code="save2026")
            self.assertTrue(result["applied"])
            self.assertEqual(result["referral_code"], "SAVE2026")

            # The customer may revise or remove attribution before payment succeeds.
            revised = set_user_referral_code(db, user_id=customer.id, code="final2026")
            self.assertTrue(revised["applied"])
            self.assertEqual(revised["referral_code"], "FINAL2026")
            db.commit()

            created = create_payment_request(
                db,
                user_id=customer.id,
                callback_url="https://example.test/api/v1/billing/callback",
                provider_name="mock",
            )
            db.commit()

            first = handle_payment_callback(
                db,
                order_public_id=created["order_id"],
                authority=created["authority"],
                status="OK",
                provider_name="mock",
                event_key="referral:success:first",
                raw_callback={"Status": "OK"},
            )
            db.commit()
            self.assertTrue(first["verified"])

            # A retry with a different event key and a conflicting status cannot
            # change a paid order, duplicate an entitlement, or rewrite its snapshot.
            replay = handle_payment_callback(
                db,
                order_public_id=created["order_id"],
                authority=created["authority"],
                status="NOK",
                provider_name="mock",
                event_key="referral:success:conflicting-replay",
                raw_callback={"Status": "NOK"},
            )
            db.commit()
            self.assertTrue(replay["verified"])
            self.assertEqual(replay["status"], "paid")

            order = db.scalar(select(Order).where(Order.public_id == created["order_id"]))
            self.assertEqual(order.status, "paid")
            self.assertEqual(order.referral_code_id, revised_code.id)
            self.assertEqual(order.referral_code_snapshot, "FINAL2026")
            self.assertEqual(order.referral_label_snapshot, "Final campaign")
            self.assertIsNotNone(order.referral_snapshot_at)

            locked_user = db.get(User, customer.id)
            self.assertIsNotNone(locked_user.referral_locked_at)
            with self.assertRaises(PermissionError):
                set_user_referral_code(db, user_id=customer.id, code="OTHER2026")

            paid_entitlements = db.scalars(
                select(Entitlement).where(
                    Entitlement.order_id == order.id,
                    Entitlement.source == "payment",
                )
            ).all()
            self.assertEqual(len(paid_entitlements), 1)

            report = get_referral_report(db, admin)
            self.assertTrue(report["snapshot_only"])
            self.assertEqual(report["paid_orders"], 1)
            self.assertEqual(report["referrals"][0]["code"], "FINAL2026")
            self.assertEqual(report["referrals"][0]["paid_orders"], 1)

            with self.assertRaises(PermissionError):
                get_referral_report(db, support)
            with self.assertRaises(PermissionError):
                get_referral_report(db, customer)

    def test_invalid_or_empty_code_does_not_block_direct_purchase(self):
        with self.SessionLocal() as db:
            admin, support, customer = self._ids(db)
            invalid = set_user_referral_code(db, user_id=customer.id, code="not valid!")
            self.assertEqual(invalid["status"], "invalid_ignored")
            self.assertTrue(invalid["purchase_allowed"])
            self.assertIsNone(db.get(User, customer.id).referral_code)

            # Empty input is explicitly direct attribution and also non-blocking.
            direct = set_user_referral_code(db, user_id=customer.id, code="")
            self.assertEqual(direct["status"], "direct")
            self.assertTrue(direct["purchase_allowed"])
            db.commit()

            created = create_payment_request(
                db,
                user_id=customer.id,
                callback_url="https://example.test/api/v1/billing/callback",
                provider_name="mock",
            )
            db.commit()
            paid = handle_payment_callback(
                db,
                order_public_id=created["order_id"],
                authority=created["authority"],
                status="OK",
                provider_name="mock",
                event_key="referral:direct:success",
            )
            db.commit()
            self.assertTrue(paid["verified"])
            order = db.scalar(select(Order).where(Order.public_id == created["order_id"]))
            self.assertEqual(order.status, "paid")
            self.assertIsNone(order.referral_code_snapshot)
            self.assertIsNotNone(order.referral_snapshot_at)

            report = get_referral_report(db, admin)
            self.assertEqual(report["paid_orders"], 1)
            self.assertEqual(report["referrals"][0]["attribution"], "direct")
            self.assertEqual(report["referrals"][0]["label"], "معرف مستقیم")

    def test_report_includes_only_paid_orders_with_snapshots(self):
        with self.SessionLocal() as db:
            admin, support, customer = self._ids(db)
            code = create_referral_code(db, admin, label="Campaign", code="CMP2026")
            db.flush()
            now = datetime.now(timezone.utc)

            referred = Order(
                public_id="report-referred",
                user_id=customer.id,
                plan_id=db.scalar(select(PremiumPlan.id).where(PremiumPlan.code == "pack_3_tests")),
                amount_minor=2_490_000,
                currency="IRR",
                status="paid",
                paid_at=now,
                referral_code_id=code.id,
                referral_code_snapshot=code.code,
                referral_label_snapshot=code.label,
                referral_snapshot_at=now,
            )
            direct = Order(
                public_id="report-direct",
                user_id=customer.id,
                plan_id=referred.plan_id,
                amount_minor=2_490_000,
                currency="IRR",
                status="paid",
                paid_at=now,
                referral_code_id=None,
                referral_code_snapshot=None,
                referral_label_snapshot=None,
                referral_snapshot_at=now,
            )
            historical_paid_without_snapshot = Order(
                public_id="report-legacy",
                user_id=customer.id,
                plan_id=referred.plan_id,
                amount_minor=2_490_000,
                currency="IRR",
                status="paid",
                paid_at=now,
                referral_snapshot_at=None,
            )
            pending_with_snapshot = Order(
                public_id="report-pending",
                user_id=customer.id,
                plan_id=referred.plan_id,
                amount_minor=2_490_000,
                currency="IRR",
                status="pending",
                paid_at=None,
                referral_code_id=code.id,
                referral_code_snapshot=code.code,
                referral_label_snapshot=code.label,
                referral_snapshot_at=now,
            )
            db.add_all([
                referred,
                direct,
                historical_paid_without_snapshot,
                pending_with_snapshot,
            ])
            db.commit()

            report = get_referral_report(db, admin)
            self.assertEqual(report["paid_orders"], 2)
            self.assertEqual(
                sorted(item["attribution"] for item in report["referrals"]),
                ["direct", "referral_code"],
            )
            self.assertTrue(
                all(item["paid_orders"] == 1 for item in report["referrals"])
            )
            self.assertEqual(report["currency_totals"][0]["gross_amount_minor"], 4_980_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
