from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import Integer, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import password_reset_service as prs
from billing_models import AuthSession, Entitlement, Order, Payment, PaymentEvent, PhoneVerification, PremiumPlan, User
from database import get_db
from main_v2 import app
from models import Base


class PasswordResetHttpE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # TestClient executes requests in a worker thread. StaticPool keeps the
        # in-memory SQLite database on the same connection across threads.
        # AuthSession.id, Entitlement.id and PhoneVerification.id are BigInteger
        # for PostgreSQL; SQLite only auto-generates a rowid for INTEGER PRIMARY KEY.
        cls._original_auth_session_id_type = AuthSession.__table__.c.id.type
        cls._original_entitlement_id_type = Entitlement.__table__.c.id.type
        cls._original_phone_verification_id_type = PhoneVerification.__table__.c.id.type
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        AuthSession.__table__.c.id.type = Integer()
        Entitlement.__table__.c.id.type = Integer()
        PhoneVerification.__table__.c.id.type = Integer()
        Base.metadata.create_all(
            cls.engine,
            tables=[
                User.__table__,
                AuthSession.__table__,
                PhoneVerification.__table__,
                PremiumPlan.__table__,
                Order.__table__,
                Payment.__table__,
                PaymentEvent.__table__,
                Entitlement.__table__,
            ],
        )
        cls.Session = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)

        def override_get_db():
            db = cls.Session()
            try:
                yield db
            finally:
                db.close()

        cls._old_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(cls._old_overrides)
        cls.engine.dispose()
        AuthSession.__table__.c.id.type = cls._original_auth_session_id_type
        Entitlement.__table__.c.id.type = cls._original_entitlement_id_type
        PhoneVerification.__table__.c.id.type = cls._original_phone_verification_id_type

    def setUp(self):
        db = self.Session()
        try:
            plan = PremiumPlan(
                id=1,
                code="free_1_test",
                name_fa="تست رایگان",
                plan_type="credits",
                duration_days=None,
                credits_granted=1,
                price_minor=0,
                currency="IRR",
                is_active=True,
                features={},
            )
            user = User(
                id=100,
                public_id="reset-http-e2e-user",
                name="Reset E2E User",
                phone="09129998877",
                password_hash=prs.hash_password("OldPassword123"),
                role="user",
                status="active",
            )
            db.add_all([plan, user])
            db.commit()
        finally:
            db.close()

    def tearDown(self):
        db = self.Session()
        try:
            db.query(Entitlement).delete()
            db.query(PhoneVerification).delete()
            db.query(AuthSession).delete()
            db.query(User).delete()
            db.query(PremiumPlan).delete()
            db.commit()
        finally:
            db.close()

    def test_login_request_otp_confirm_reset_and_old_session_rejected(self):
        login = self.client.post(
            "/api/v1/auth/login",
            json={"phone": "09129998877", "password": "OldPassword123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        old_token = login.json()["token"]
        self.assertEqual(login.json()["quota"], 1)

        sent: dict[str, str] = {}
        with patch.object(prs, "_send_reset_otp", side_effect=lambda phone, code: sent.update(phone=phone, code=code)):
            requested = self.client.post(
                "/api/v1/auth/password-reset/request",
                json={"phone": "09129998877"},
            )
        self.assertEqual(requested.status_code, 200, requested.text)
        payload = requested.json()
        self.assertTrue(payload["otp_required"])
        self.assertIn("challenge_id", payload)
        self.assertEqual(sent["phone"], "09129998877")

        confirmed = self.client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "challenge_id": payload["challenge_id"],
                "code": sent["code"],
                "new_password": "NewPassword456",
            },
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        new_token = confirmed.json()["token"]
        self.assertNotEqual(new_token, old_token)
        self.assertTrue(confirmed.json()["password_reset"])

        old_me = self.client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        self.assertEqual(old_me.status_code, 401, old_me.text)

        new_me = self.client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        self.assertEqual(new_me.status_code, 200, new_me.text)
        self.assertEqual(new_me.json()["user"]["phone"], "09129998877")

        old_password_login = self.client.post(
            "/api/v1/auth/login",
            json={"phone": "09129998877", "password": "OldPassword123"},
        )
        self.assertEqual(old_password_login.status_code, 401)

        new_password_login = self.client.post(
            "/api/v1/auth/login",
            json={"phone": "09129998877", "password": "NewPassword456"},
        )
        self.assertEqual(new_password_login.status_code, 200, new_password_login.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
