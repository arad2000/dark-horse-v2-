from __future__ import annotations

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from admin_service import grant_credits, list_user_summary, revoke_entitlement
from billing_models import Entitlement, PremiumPlan, User
from models import Base


class AdminServiceTests(unittest.TestCase):
    """Run Admin Service persistence tests against the configured staging PostgreSQL DB."""

    @classmethod
    def setUpClass(cls):
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise unittest.SkipTest("DATABASE_URL is required for PostgreSQL admin persistence tests")
        cls.engine = create_engine(database_url, future=True)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False, future=True)
        _ = (Entitlement, PremiumPlan)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add_all([
                User(public_id="admin-1", name="Admin", phone="09000000001", role="admin", status="active"),
                User(public_id="user-1", name="User", phone="09000000002", role="user", status="active"),
                User(public_id="support-1", name="Support", phone="09000000003", role="support", status="active"),
                PremiumPlan(code="pack_3_tests", name_fa="بسته ۳ تست", plan_type="credits", duration_days=None, credits_granted=3, price_minor=2_490_000, currency="IRR", is_active=True, features={"tests": 3, "non_expiring": True}),
            ])
            db.commit()

    def test_non_admin_cannot_grant(self):
        with self.SessionLocal() as db:
            actor = db.query(User).filter_by(public_id="user-1").one()
            with self.assertRaises(PermissionError):
                grant_credits(db, actor, user_id=actor.id, plan_code="pack_3_tests", reason="manual correction")

    def test_grant_requires_reason_and_is_audited(self):
        with self.SessionLocal() as db:
            actor = db.query(User).filter_by(public_id="admin-1").one()
            target = db.query(User).filter_by(public_id="user-1").one()
            with self.assertRaises(ValueError):
                grant_credits(db, actor, user_id=target.id, plan_code="pack_3_tests", reason="")
            entitlement = grant_credits(db, actor, user_id=target.id, plan_code="pack_3_tests", reason="support request #123")
            db.commit()
            self.assertEqual(entitlement.credits_granted, 3)
            self.assertEqual(entitlement.credits_remaining, 3)
            self.assertEqual(len(actor.admin_audit_logs), 1)
            self.assertEqual(actor.admin_audit_logs[0].action, "grant_credits")

    def test_revoke_zeroes_remaining_credit_and_is_audited(self):
        with self.SessionLocal() as db:
            actor = db.query(User).filter_by(public_id="admin-1").one()
            target = db.query(User).filter_by(public_id="user-1").one()
            ent = grant_credits(db, actor, user_id=target.id, plan_code="pack_3_tests", reason="grant")
            db.commit()
            updated = revoke_entitlement(db, actor, entitlement_id=ent.id, reason="fraud review")
            db.commit()
            self.assertEqual(updated.status, "revoked")
            self.assertEqual(updated.credits_remaining, 0)
            self.assertTrue(any(log.action == "revoke_entitlement" for log in actor.admin_audit_logs))

    def test_user_summary_omits_sensitive_password(self):
        with self.SessionLocal() as db:
            actor = db.query(User).filter_by(public_id="admin-1").one()
            rows = list_user_summary(db, actor)
            self.assertTrue(rows)
            self.assertNotIn("password_hash", rows[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
