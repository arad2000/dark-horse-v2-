from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from admin_http_api import app


class AdminHttpApiTests(unittest.TestCase):
    def test_requires_bearer_token(self):
        client = TestClient(app)
        response = client.get("/api/v1/admin/dashboard")
        self.assertEqual(response.status_code, 401)

    @patch("admin_http_api.SessionLocal")
    def test_forbids_non_admin(self, session_local):
        class DummyDb:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        session_local.return_value = DummyDb()

        from billing_models import User
        fake_user = User(id=5, public_id="u5", name="User", phone="0900", role="user", status="active")
        with patch("admin_http_api.resolve_session", return_value=fake_user):
            client = TestClient(app)
            response = client.get(
                "/api/v1/admin/dashboard",
                headers={"Authorization": "Bearer token"},
            )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
