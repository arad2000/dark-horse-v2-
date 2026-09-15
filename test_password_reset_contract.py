import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class PasswordResetContractTests(unittest.TestCase):
    def test_server_flow_exists_with_phone_otp_and_session_invalidation(self):
        service = (ROOT / "password_reset_service.py").read_text(encoding="utf-8")
        self.assertIn('purpose="password_reset"', service)
        self.assertIn("MAX_ATTEMPTS", service)
        self.assertIn("verify_password", service)
        self.assertIn("revoke_all_sessions", service)
        self.assertIn("_hash_code", service)

    def test_api_exposes_request_and_confirm_endpoints(self):
        api = (ROOT / "commercial_api.py").read_text(encoding="utf-8")
        self.assertIn('from password_reset_service import request_password_reset_otp, reset_password_with_otp', api)
        self.assertIn('@router.post("/auth/password-reset/request")', api)
        self.assertIn('@router.post("/auth/password-reset/confirm")', api)

    def test_client_exposes_reset_methods(self):
        js = (DOCS / "auth_api_client.js").read_text(encoding="utf-8")
        self.assertIn("requestPasswordReset(phone)", js)
        self.assertIn("resetPassword(challengeId, code, newPassword)", js)

    def test_auth_ui_has_forgot_password_path(self):
        js = (DOCS / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertIn("فراموشی رمز عبور", js)
        self.assertIn("requestPasswordReset", js)
        self.assertIn("resetPassword", js)
        self.assertIn("کد تأیید", js)


if __name__ == "__main__":
    unittest.main()
