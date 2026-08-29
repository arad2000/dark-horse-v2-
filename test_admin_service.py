from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from admin_service import grant_credits, list_user_summary, revoke_entitlement
from billing_models import Entitlement, PremiumPlan, User
from models import Base


class AdminServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False)
        _ = (Entitlement, PremiumPlan)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add_all([
                User(id=1, public_id="admin-1", name="Admin", phone="09000000001", role="admin", status="active"),
                User(id=2, public_id="user-1", name="User", phone="09000000002", role="user", status="active"),
                User(id=3, public_id="support-1", name="Support", phone="09000000003", role="support", status="active"),
                PremiumPlan(id=1, code="pack_3_tests", name_fa="بسته ۳ تست", plan_type="credits", duration_days=None, credits_granted=3, price_minor=2_490_000, currency="IRR", is_active=True, features={"tests": 3, "non_expiring": True}),
            ])
            db.commit()

    def test_non_admin_cannot_grant(self):
        with self.SessionLocal() as db:
            actor = db.get(User, 2)
            with self.assertRaises(PermissionError):
                grant_credits(db, actor, user_id=2, plan_code="pack_3_tests", reason="manual correction")

    def test_grant_requires_reason_and_is_audited(self):
        with self.SessionLocal() as db:
            actor = db.get(User, 1)
            with self.assertRaises(ValueError):
                grant_credits(db, actor, user_id=2, plan_code="pack_3_tests", reason="")
            entitlement = grant_credits(db, actor, user_id=2, plan_code="pack_3_tests", reason="support request #123")
            db.commit()
            self.assertEqual(entitlement.credits_granted, 3)
            self.assertEqual(entitlement.credits_remaining, 3)
            self.assertEqual(len(actor.admin_audit_logs), 1)
            self.assertEqual(actor.admin_audit_logs[0].action, "grant_credits")

    def test_revoke_zeroes_remaining_credit_and_is_audited(self):
        with self.SessionLocal() as db:
            actor = db.get(User, 1)
            ent = grant_credits(db, actor, user_id=2, plan_code="pack_3_tests", reason="grant")
            db.commit()
            updated = revoke_entitlement(db, actor, entitlement_id=ent.id, reason="fraud review")
            db.commit()
            self.assertEqual(updated.status, "revoked")
            self.assertEqual(updated.credits_remaining, 0)
            self.assertTrue(any(log.action == "revoke_entitlement" for log in actor.admin_audit_logs))

    def test_user_summary_omits_sensitive_password(self):
        with self.SessionLocal() as db:
            actor = db.get(User, 1)
            rows = list_user_summary(db, actor)
            self.assertTrue(rows)
            self.assertNotIn("password_hash", rows[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
