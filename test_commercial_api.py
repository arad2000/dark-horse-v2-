from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from billing_models import PremiumPlan
from database import get_db
from models import Base
from main_v2 import app


class CommercialApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(cls.engine)
        with cls.SessionLocal() as db:
            db.add_all([
                PremiumPlan(code="free_1_test", name_fa="رایگان — ۱ تست", plan_type="credits", duration_days=None, credits_granted=1, price_minor=0, currency="IRR", is_active=True, features={"tests": 1}),
                PremiumPlan(code="pack_3_tests", name_fa="بسته ۳ تست", plan_type="credits", duration_days=None, credits_granted=3, price_minor=2_490_000, currency="IRR", is_active=True, features={"tests": 3}),
            ])
            db.commit()

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_register_login_me_quota_and_consume(self):
        phone = "09120000001"
        response = self.client.post("/api/v1/auth/register", json={"name": "Test User", "phone": phone, "password": "strong-pass-123"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["token"])
        self.assertEqual(body["quota"], 1)
        self.assertEqual(body["user"]["phone"], phone)

        token = body["token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = self.client.get("/api/v1/me", headers=headers)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["public_id"], body["user"]["public_id"])

        quota = self.client.get("/api/v1/me/quota", headers=headers)
        self.assertEqual(quota.status_code, 200)
        self.assertEqual(quota.json()["credits_remaining"], 1)

        consume = self.client.post("/api/v1/me/consume-test", headers=headers)
        self.assertEqual(consume.status_code, 200, consume.text)
        self.assertEqual(consume.json()["consumed"], 1)
        self.assertEqual(consume.json()["credits_remaining"], 0)

        consume_again = self.client.post("/api/v1/me/consume-test", headers=headers)
        self.assertEqual(consume_again.status_code, 409)

    def test_duplicate_registration_and_invalid_login_fail_closed(self):
        payload = {"name": "Test User 2", "phone": "09120000002", "password": "strong-pass-123"}
        first = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(first.status_code, 200)
        duplicate = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(duplicate.status_code, 400)

        bad_login = self.client.post("/api/v1/auth/login", json={"phone": payload["phone"], "password": "wrong-pass-123"})
        self.assertEqual(bad_login.status_code, 401)

    def test_missing_bearer_is_rejected(self):
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/me/quota").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/me/consume-test").status_code, 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)
