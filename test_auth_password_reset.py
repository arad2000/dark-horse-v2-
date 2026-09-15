import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class PasswordResetContractTests(unittest.TestCase):
    def test_reset_router_is_mounted_once(self):
        api = (ROOT / "commercial_api.py").read_text(encoding="utf-8")
        service = (ROOT / "password_reset_service.py").read_text(encoding="utf-8")
        self.assertIn("from password_reset_service import attach_router", api)
        self.assertEqual(api.count("attach_router(router)"), 1)
        self.assertIn('prefix="/auth/password-reset"', service)
        self.assertIn('purpose == RESET_PURPOSE', service)
        self.assertIn('with_for_update()', service)
        self.assertIn('revoke_all_sessions(db, user.id)', service)

    def test_frontend_has_matching_reset_contract(self):
        client = (ROOT / "docs" / "auth_api_client.js").read_text(encoding="utf-8")
        ui = (ROOT / "docs" / "password_reset_ui.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/auth/password-reset/request", client)
        self.assertIn("/api/v1/auth/password-reset/confirm", client)
        self.assertIn("dh-forgot-password", ui)
        self.assertIn("dh-reset-send", ui)
        self.assertIn("dh-reset-confirm", ui)


if __name__ == "__main__":
    unittest.main()
