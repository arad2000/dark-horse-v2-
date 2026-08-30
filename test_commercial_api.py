from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from database import get_db
from main_v2 import app


class FakeDB:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class CommercialApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = FakeDB()

        def override_get_db():
            yield cls.db

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_register_contract(self):
        user = SimpleNamespace(
            id=7,
            public_id="public-7",
            name="Test User",
            phone="09120000001",
            role="user",
            status="active",
        )
        with patch("commercial_api.register_user", return_value=(user, "raw-token")), patch(
            "commercial_api.ensure_free_entitlement"
        ), patch("commercial_api._quota", return_value=1):
            response = self.client.post(
                "/api/v1/auth/register",
                json={"name": "Test User", "phone": user.phone, "password": "strong-pass-123"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"token": "raw-token", "user": {
            "id": 7,
            "public_id": "public-7",
            "name": "Test User",
            "phone": "09120000001",
            "role": "user",
            "status": "active",
        }, "quota": 1})

    def test_login_contract(self):
        user = SimpleNamespace(
            id=8,
            public_id="public-8",
            name="Login User",
            phone="09120000002",
            role="user",
            status="active",
        )
        with patch("commercial_api.authenticate_user", return_value=(user, "login-token")), patch(
            "commercial_api.ensure_free_entitlement"
        ), patch("commercial_api._quota", return_value=1):
            response = self.client.post(
                "/api/v1/auth/login",
                json={"phone": user.phone, "password": "strong-pass-123"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["token"], "login-token")
        self.assertEqual(response.json()["quota"], 1)

    def test_bearer_protection_and_me(self):
        user = SimpleNamespace(
            id=9,
            public_id="public-9",
            name="Me User",
            phone="09120000003",
            role="user",
            status="active",
        )
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)
        with patch("commercial_api.resolve_session", return_value=user):
            response = self.client.get("/api/v1/me", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["public_id"], "public-9")

    def test_quota_contract(self):
        user = SimpleNamespace(id=10)
        with patch("commercial_api.resolve_session", return_value=user), patch(
            "commercial_api._quota", return_value=3
        ):
            response = self.client.get("/api/v1/me/quota", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"credits_remaining": 3, "user_id": 10})

    def test_consume_contract(self):
        user = SimpleNamespace(
            id=11,
            public_id="public-11",
            name="Consume User",
            phone="09120000004",
            role="user",
            status="active",
        )
        entitlement = SimpleNamespace(id=55)
        with patch("commercial_api.resolve_session", return_value=user), patch(
            "commercial_api.consume_one_test", return_value=entitlement
        ), patch("commercial_api._quota", return_value=2):
            response = self.client.post("/api/v1/me/consume-test", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["consumed"], 1)
        self.assertEqual(response.json()["credits_remaining"], 2)
        self.assertEqual(response.json()["entitlement_id"], 55)


if __name__ == "__main__":
    unittest.main(verbosity=2)
