import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class PasswordResetContractTests(unittest.TestCase):
    def test_backend_password_reset_contract(self):
        api = (ROOT / "commercial_api.py").read_text(encoding="utf-8")
        service = (ROOT / "password_reset_service.py").read_text(encoding="utf-8")
        auth = (ROOT / "auth_service.py").read_text(encoding="utf-8")
        self.assertIn('/auth/password/reset/request', api)
        self.assertIn('/auth/password/reset/verify', api)
        self.assertIn('request_password_reset_otp', api)
        self.assertIn('reset_password_with_otp', api)
        self.assertIn('purpose == RESET_PURPOSE', service)
        self.assertIn('revoke_all_sessions(db, user.id)', service)
        self.assertIn('def revoke_all_sessions', auth)

    def test_frontend_password_reset_contract(self):
        client = (ROOT / 'docs' / 'auth_api_client.js').read_text(encoding='utf-8')
        ui = (ROOT / 'docs' / 'password_reset_ui.js').read_text(encoding='utf-8')
        index = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('requestPasswordReset', client)
        self.assertIn('verifyPasswordReset', client)
        self.assertIn('dh-c-forgot', ui)
        self.assertIn('dh-reset-submit', ui)
        self.assertIn('password_reset_ui.js', index)


if __name__ == '__main__':
    unittest.main()
