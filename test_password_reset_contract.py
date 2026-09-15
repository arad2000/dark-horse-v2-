import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class PasswordResetContractTests(unittest.TestCase):
    def test_server_flow_exists_with_phone_otp_and_session_invalidation(self):
        service = (ROOT / "password_reset_service.py").read_text(encoding="utf-8")
        self.assertIn('RESET_PURPOSE = "password_reset"', service)
        self.assertIn("MAX_ATTEMPTS", service)
        self.assertIn("hash_password", service)
        self.assertIn("revoke_all_sessions", service)
        self.assertIn("_hash_code", service)
        self.assertIn('KAVENEGAR_RESET_OTP_TEMPLATE', service)

    def test_commercial_router_exposes_password_reset_endpoints(self):
        import commercial_api
        paths = {getattr(route, "path", "") for route in commercial_api.router.routes}
        self.assertIn("/api/v1/auth/password-reset/request", paths)
        self.assertIn("/api/v1/auth/password-reset/confirm", paths)

    def test_main_app_imports_without_breaking(self):
        import main_v2
        self.assertIsNotNone(main_v2.app)
        self.assertIsNotNone(main_v2.commercial_router)

    def test_client_exposes_reset_methods(self):
        js = (DOCS / "auth_api_client.js").read_text(encoding="utf-8")
        self.assertIn("requestPasswordReset(phone)", js)
        self.assertIn("resetPassword(challengeId, code, newPassword)", js)
        self.assertIn("/api/v1/auth/password-reset/request", js)
        self.assertIn("/api/v1/auth/password-reset/confirm", js)

    def test_auth_ui_has_forgot_password_path(self):
        js = (DOCS / "password_reset_ui.js").read_text(encoding="utf-8")
        self.assertIn("فراموشی رمز عبور", js)
        self.assertIn("requestPasswordReset", js)
        self.assertIn("resetPassword", js)
        self.assertIn("کد تأیید", js)
        self.assertIn("autocomplete=\"one-time-code\"", js)

    def test_home_loads_reset_ui_after_auth_client(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        auth_pos = html.index('src="auth_api_client.js"')
        reset_pos = html.index('src="password_reset_ui.js?v=1"')
        self.assertLess(auth_pos, reset_pos)


if __name__ == "__main__":
    unittest.main()
