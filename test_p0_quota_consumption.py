from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from auth_service import hash_password, issue_session
from billing_models import AuthSession, Entitlement, JourneyCreditConsumption, PremiumPlan, User
from database import engine, get_db
from main_v2 import app
from models import Base, UserSession


class P0QuotaConsumptionTests(unittest.TestCase):
    """Production-shaped regression: missing sessions charge and retries do not."""

    @classmethod
    def setUpClass(cls):
        if not os.getenv("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL is required for PostgreSQL P0 E2E")
        cls.client = TestClient(app)
        with engine.begin() as connection:
            Base.metadata.create_all(connection)

    def setUp(self):
        with next(get_db()) as db:
            db.execute(delete(JourneyCreditConsumption))
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
                    starts_at=datetime.now(timezone.utc),
                    expires_at=None,
                    status="active",
                )
            )
            token, _ = issue_session(db, user)
            db.commit()
            self.token = token
            self.user_id = user.id

    def _new_session(self, session_uuid: str, *, completed: bool = False) -> None:
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

    def test_missing_session_is_provisioned_and_each_journey_charges_once(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        first_uuid = str(uuid4())
        second_uuid = str(uuid4())

        self._new_session(first_uuid, completed=True)

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

        with next(get_db()) as db:
            self.assertIsNone(db.scalar(select(UserSession).where(UserSession.session_uuid == second_uuid)))

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

        second_retry = self.client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": second_uuid},
        )
        self.assertEqual(second_retry.status_code, 200, second_retry.text)
        self.assertEqual(second_retry.json()["consumed"], 0)
        self.assertTrue(second_retry.json()["already_consumed"])
        self.assertEqual(second_retry.json()["credits_remaining"], 1)
        self.assertEqual(second_retry.json()["credits_consumed"], 2)

        with TestClient(app) as fresh_client:
            cold = fresh_client.get("/api/v1/me/quota", headers=headers)
        self.assertEqual(cold.status_code, 200, cold.text)
        self.assertEqual(cold.json(), {"credits_granted": 3, "credits_consumed": 2, "credits_remaining": 1})

        with next(get_db()) as db:
            ledger = list(
                db.scalars(
                    select(JourneyCreditConsumption)
                    .where(JourneyCreditConsumption.user_id == self.user_id)
                )
            )
            self.assertEqual(len(ledger), 2)
            self.assertEqual({row.session_uuid for row in ledger}, {first_uuid, second_uuid})
            first = db.scalar(select(UserSession).where(UserSession.session_uuid == first_uuid))
            second = db.scalar(select(UserSession).where(UserSession.session_uuid == second_uuid))
            self.assertTrue(first.is_completed)
            self.assertFalse(second.is_completed)


if __name__ == "__main__":
    unittest.main(verbosity=2)