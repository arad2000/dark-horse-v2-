import unittest
from pathlib import Path
from unittest.mock import patch

from payment_providers import MockPaymentProvider

ROOT = Path(__file__).resolve().parent
COMMERCIAL_UI = ROOT / "docs" / "commercial_ui.js"
ADMIN_HTML = ROOT / "docs" / "admin.html"


class SandboxPaymentAdminUiTests(unittest.TestCase):
    def test_mock_provider_returns_canonical_sandbox_screen(self):
        provider = MockPaymentProvider(authority="MOCK-AUTH-TEST", transaction_id="MOCK-REF-TEST")
        with patch.dict("os.environ", {"FRONTEND_APP_URL": "https://asbe-siah.ir"}, clear=False):
            result = provider.request_payment(
                amount_rial=2_490_000,
                order_public_id="ORDER-TEST",
                callback_url="https://api.asbe-siah.ir/api/v1/billing/callback?order_id=ORDER-TEST",
            )
        self.assertIn("https://asbe-siah.ir/?payment_sandbox=1", result["payment_url"])
        self.assertIn("order_id=ORDER-TEST", result["payment_url"])
        self.assertIn("authority=MOCK-AUTH-TEST", result["payment_url"])

    def test_mock_provider_verification_is_deterministic(self):
        provider = MockPaymentProvider(authority="AUTH", transaction_id="REF")
        self.assertTrue(provider.verify_payment(amount_rial=2_490_000, authority="AUTH")["verified"])
        self.assertFalse(provider.verify_payment(amount_rial=2_490_000, authority="OTHER")["verified"])

    def test_frontend_has_sandbox_callback_and_admin_entrypoint(self):
        ui = COMMERCIAL_UI.read_text(encoding="utf-8")
        admin = ADMIN_HTML.read_text(encoding="utf-8")
        self.assertIn("payment_sandbox", ui)
        self.assertIn("/api/v1/billing/callback", ui)
        self.assertIn("Status: status", ui)
        self.assertIn("id=\"dh-admin-link\"", ui)
        self.assertIn("href = 'admin.html'", ui)
        self.assertIn("/api/v1/admin/dashboard", admin)
        self.assertIn("/api/v1/admin/users?limit=50", admin)
        self.assertIn("/api/v1/admin/feedback?limit=30", admin)

    def test_admin_ui_checks_server_role_before_loading(self):
        admin = ADMIN_HTML.read_text(encoding="utf-8")
        self.assertIn("u.role!=='admin'&&u.role!=='support'", admin)
        self.assertIn("Authorization':'Bearer '+t", admin)


if __name__ == "__main__":
    unittest.main()
