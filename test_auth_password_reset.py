import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class PasswordResetContractTests(unittest.TestCase):
    def test_backend_exposes_password_reset_flow(self):
        api = (ROOT / "commercial_api.py").read_text(encoding="utf-8")
        service = (ROOT / "phone_verification_service.py").read_text(encoding="utf-8")
        auth = (ROOT / "auth_service.py").read_text(encoding="utf-8")
        self.assertIn("/auth/password/reset/request", api)
        self.assertIn("/auth/password/reset/verify", api)
        self.assertIn("request_password_reset_otp", api)
        self.assertIn("verify_password_reset_otp", api)
        self.assertIn('purpose == "reset_password"', service)
        self.assertIn("revoke_all_sessions", auth)

    def test_frontend_exposes_forgot_password_action(self):
        client = (ROOT / "docs" / "auth_api_client.js").read_text(encoding="utf-8")
        ui = (ROOT / "docs" / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertIn("requestPasswordReset", client)
        self.assertIn("verifyPasswordReset", client)
        self.assertIn("dh-c-forgot", ui)
        self.assertIn("dh-reset-submit", ui)


if __name__ == "__main__":
    unittest.main()
