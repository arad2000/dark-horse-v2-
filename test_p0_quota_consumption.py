from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from auth_service import hash_password, issue_session
from billing_models import Entitlement, JourneyCreditConsumption, PremiumPlan, User
from database import engine, get_db
from main_v2 import app
from models import Base, UserSession


class P0HybridQuotaConsumptionTests(unittest.TestCase):
    """Three-credit journey test: retries are idempotent, new journeys charge."""

    @classmethod
    def setUpClass(cls):
        if not os.getenv("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL is required for PostgreSQL P0 E2E")
        cls.client = TestClient(app)
        with engine.begin() as connection:
            Base.metadata.create_all(connection)

    def setUp(self):
        with next(get_db()) as db:
            suffix = uuid4().hex[:10]
            plan = PremiumPlan(
                code=f"p0_pack_{suffix}",
                name_fa="P0 ۳ تست",
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
                name="P0 Hybrid Quota User",
                phone="09" + str(100000000 + int(suffix[:8], 16) % 899999999).zfill(9),
                password_hash=hash_password("P0-Hybrid-Quota-2026!"),
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
                    starts_at=datetime.now(timezone.utc),
                    expires_at=None,
                    status="active",
                )
            )
            token, _ = issue_session(db, user)
            db.commit()
            self.token = token
            self.user_id = user.id

    def _new_session(self, session_uuid: str, *, completed: bool) -> None:
        with next(get_db()) as db:
            db.add(
                UserSession(
                    user_id=self.user_id,
                    session_uuid=session_uuid,
                    micro_motives=[],
                    sjt_answers={},
                    conjoint_choices={},
                    is_completed=completed,
                )
            )
            db.commit()

    def test_same_session_is_idempotent_and_second_session_charges(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        first_uuid = str(uuid4())
        second_uuid = str(uuid4())

        # Result completion is deliberately true before first billing request.
        self._new_session(first_uuid, completed=True)
        self._new_session(second_uuid, completed=False)

        first = self.client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": first_uuid},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["consumed"], 1)
        self.assertFalse(first.json()["already_consumed"])
        self.assertEqual(first.json()["credits_remaining"], 2)
        self.assertEqual(first.json()["credits_consumed"], 1)

        retry = self.client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": first_uuid},
        )
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()["consumed"], 0)
        self.assertTrue(retry.json()["already_consumed"])
        self.assertEqual(retry.json()["credits_remaining"], 2)
        self.assertEqual(retry.json()["credits_consumed"], 1)

        second = self.client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": second_uuid},
        )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["consumed"], 1)
        self.assertFalse(second.json()["already_consumed"])
        self.assertEqual(second.json()["credits_remaining"], 1)
        self.assertEqual(second.json()["credits_consumed"], 2)

        quota = self.client.get("/api/v1/me/quota", headers=headers)
        self.assertEqual(quota.status_code, 200, quota.text)
        self.assertEqual(quota.json()["credits_granted"], 3)
        self.assertEqual(quota.json()["credits_consumed"], 2)
        self.assertEqual(quota.json()["credits_remaining"], 1)

        with next(get_db()) as db:
            ledger = list(
                db.scalars(
                    select(JourneyCreditConsumption)
                    .where(JourneyCreditConsumption.user_id == self.user_id)
                )
            )
            self.assertEqual(len(ledger), 2)
            self.assertEqual({row.session_uuid for row in ledger}, {first_uuid, second_uuid})
            self.assertTrue(db.scalar(select(UserSession).where(UserSession.session_uuid == first_uuid)).is_completed)
            self.assertFalse(db.scalar(select(UserSession).where(UserSession.session_uuid == second_uuid)).is_completed)


if __name__ == "__main__":
    unittest.main(verbosity=2)