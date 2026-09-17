from __future__ import annotations

import os
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from auth_service import hash_password, issue_session
from billing_models import AuthSession, Entitlement, PremiumPlan, User
from database import engine, get_db
from main_v2 import app
from models import Base, UserSession


class P0QuotaConsumptionTests(unittest.TestCase):
    """Production-shaped regression: one journey UUID can consume at most one credit."""

    @classmethod
    def setUpClass(cls):
        if not os.getenv("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL is required for PostgreSQL P0 E2E")
        cls.client = TestClient(app)
        with engine.begin() as connection:
            Base.metadata.create_all(connection)

    def setUp(self):
        with next(get_db()) as db:
            db.execute(delete(AuthSession))
            db.execute(delete(Entitlement))
            db.execute(delete(UserSession))
            db.execute(delete(User))
            db.execute(delete(PremiumPlan))
            db.commit()

            plan = PremiumPlan(
                code="pack_3_tests",
                name_fa="بسته ۳ تست",
                plan_type="credits",
                duration_days=None,
                credits_granted=3,
                price_minor=2_490_000,
                currency="IRR",
                is_active=True,
                features={"tests": 3, "non_expiring": True},
            )
            user = User(
                public_id=str(uuid4()),
                name="P0 Quota User",
                phone="09123334455",
                password_hash=hash_password("P0-Quota-Test-2026!"),
                role="user",
                status="active",
            )
            db.add_all([plan, user])
            db.flush()
            db.add(
                Entitlement(
                    user_id=user.id,
                    plan_id=plan.id,
                    source="payment",
                    credits_granted=3,
                    credits_remaining=3,
                    starts_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                    expires_at=None,
                    status="active",
                )
            )
            token, _ = issue_session(db, user)
            db.commit()
            cls.token = token
            cls.user_id = user.id

    def test_same_journey_is_charged_once_and_next_journey_charges_once(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        session_one = str(uuid4())
        session_two = str(uuid4())

        with next(get_db()) as db:
            db.add(
                UserSession(
                    user_id=self.user_id,
                    session_uuid=session_one,
                    micro_motives=[],
                    sjt_answers={},
                    conjoint_choices={},
                    is_completed=False,
                )
            )
            db.add(
                UserSession(
                    user_id=self.user_id,
                    session_uuid=session_two,
                    micro_motives=[],
                    sjt_answers={},
                    conjoint_choices={},
                    is_completed=False,
                )
            )
            db.commit()

        first = self.client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": session_one},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["consumed"], 1)
        self.assertFalse(first.json()["already_consumed"])
        self.assertEqual(first.json()["credits_remaining"], 2)
        self.assertEqual(first.json()["credits_consumed"], 1)

        retry = self.client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": session_one},
        )
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()["consumed"], 0)
        self.assertTrue(retry.json()["already_consumed"])
        self.assertEqual(retry.json()["credits_remaining"], 2)
        self.assertEqual(retry.json()["credits_consumed"], 1)

        second = self.client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": session_two},
        )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["consumed"], 1)
        self.assertFalse(second.json()["already_consumed"])
        self.assertEqual(second.json()["credits_remaining"], 1)
        self.assertEqual(second.json()["credits_consumed"], 2)

        quota = self.client.get("/api/v1/me/quota", headers=headers)
        self.assertEqual(quota.status_code, 200, quota.text)
        self.assertEqual(
            quota.json(),
            {"credits_granted": 3, "credits_consumed": 2, "credits_remaining": 1},
        )

        with next(get_db()) as db:
            rows = list(db.scalars(select(Entitlement).where(Entitlement.user_id == self.user_id)))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].credits_remaining, 1)
            one = db.scalar(select(UserSession).where(UserSession.session_uuid == session_one))
            two = db.scalar(select(UserSession).where(UserSession.session_uuid == session_two))
            self.assertTrue(one.is_completed)
            self.assertTrue(two.is_completed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
