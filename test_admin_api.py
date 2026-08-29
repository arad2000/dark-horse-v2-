from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from admin_api import admin_grant_credits, admin_revoke_entitlement, dashboard_summary
from billing_models import AdminAuditLog, Entitlement, PremiumPlan, User
from models import Base


class AdminApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False)
        _ = (AdminAuditLog, Entitlement, PremiumPlan)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add_all([
                User(id=1, public_id="admin-1", name="Admin", phone="09100000000", role="admin", status="active"),
                User(id=2, public_id="user-1", name="User", phone="09200000000", role="user", status="active"),
                PremiumPlan(id=1, code="pack_3_tests", name_fa="بسته ۳ تست", plan_type="credits", duration_days=None, credits_granted=3, price_minor=2_490_000, currency="IRR", is_active=True, features={"tests": 3, "non_expiring": True}),
            ])
            db.commit()

    def test_dashboard_requires_admin_and_is_operational_only(self):
        with self.SessionLocal() as db:
            admin = db.get(User, 1)
            user = db.get(User, 2)
            summary = dashboard_summary(db, admin)
            self.assertEqual(summary["users_total"], 2)
            with self.assertRaises(PermissionError):
                dashboard_summary(db, user)

    def test_grant_and_revoke_are_audited(self):
        with self.SessionLocal() as db:
            admin = db.get(User, 1)
            result = admin_grant_credits(db, admin, user_id=2, plan_code="pack_3_tests", reason="Support correction")
            db.commit()
            self.assertEqual(result["credits_granted"], 3)
            entitlement_id = result["entitlement_id"]
            self.assertEqual(db.query(AdminAuditLog).count(), 1)

            revoked = admin_revoke_entitlement(db, admin, entitlement_id=entitlement_id, reason="Fraud review")
            db.commit()
            self.assertEqual(revoked["status"], "revoked")
            self.assertEqual(revoked["credits_remaining"], 0)
            self.assertEqual(db.query(AdminAuditLog).count(), 2)

    def test_reason_is_required(self):
        with self.SessionLocal() as db:
            admin = db.get(User, 1)
            with self.assertRaises(ValueError):
                admin_grant_credits(db, admin, user_id=2, plan_code="pack_3_tests", reason="  ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
