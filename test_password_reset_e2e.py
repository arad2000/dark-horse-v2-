from __future__ import annotations

import secrets
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete

from auth_service import hash_password, issue_session
from billing_models import AuthSession, PhoneVerification, User
from database import SessionLocal
from main_v2 import app


def _unique_phone() -> str:
    digits = "".join(ch for ch in secrets.token_hex(8) if ch.isdigit())
    digits = (digits + "123456789")[:9]
    return "09" + digits


class PasswordResetE2ETests(unittest.TestCase):
    def test_full_http_reset_flow_invalidates_old_auth(self):
        phone = _unique_phone()
        db = SessionLocal()
        user = User(
            public_id=secrets.token_hex(18),
            name="Password Reset E2E",
            phone=phone,
            password_hash=hash_password("OldPassword123"),
            role="user",
            status="active",
        )
        db.add(user)
        db.flush()
        old_token, _ = issue_session(db, user)
        db.commit()
        user_id = int(user.id)
        db.close()

        sent: dict[str, str] = {}
        try:
            with patch("password_reset_service._send_reset_otp", side_effect=lambda p, c: sent.update(phone=p, code=c)):
                with TestClient(app) as client:
                    request_response = client.post(
                        "/api/v1/auth/password-reset/request",
                        json={"phone": phone},
                    )
                    self.assertEqual(request_response.status_code, 200, request_response.text)
                    request_payload = request_response.json()
                    self.assertTrue(request_payload["otp_required"])
                    self.assertIn("challenge_id", request_payload)
                    self.assertEqual(sent["phone"], phone)

                    confirm_response = client.post(
                        "/api/v1/auth/password-reset/confirm",
                        json={
                            "challenge_id": request_payload["challenge_id"],
                            "code": sent["code"],
                            "new_password": "NewPassword123",
                        },
                    )
                    self.assertEqual(confirm_response.status_code, 200, confirm_response.text)
                    confirm_payload = confirm_response.json()
                    self.assertTrue(confirm_payload["password_reset"])
                    new_token = confirm_payload["token"]
                    self.assertTrue(new_token)

                    old_me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {old_token}"})
                    self.assertEqual(old_me.status_code, 401)

                    new_me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {new_token}"})
                    self.assertEqual(new_me.status_code, 200, new_me.text)
                    self.assertEqual(new_me.json()["user"]["phone"], phone)

                    old_login = client.post(
                        "/api/v1/auth/login",
                        json={"phone": phone, "password": "OldPassword123"},
                    )
                    self.assertEqual(old_login.status_code, 401)

                    new_login = client.post(
                        "/api/v1/auth/login",
                        json={"phone": phone, "password": "NewPassword123"},
                    )
                    self.assertEqual(new_login.status_code, 200, new_login.text)
                    self.assertTrue(new_login.json()["token"])

                    replay = client.post(
                        "/api/v1/auth/password-reset/confirm",
                        json={
                            "challenge_id": request_payload["challenge_id"],
                            "code": sent["code"],
                            "new_password": "AnotherPassword123",
                        },
                    )
                    self.assertEqual(replay.status_code, 400, replay.text)
        finally:
            cleanup = SessionLocal()
            try:
                cleanup.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
                cleanup.execute(delete(PhoneVerification).where(PhoneVerification.phone == phone))
                cleanup.execute(delete(User).where(User.id == user_id))
                cleanup.commit()
            finally:
                cleanup.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
