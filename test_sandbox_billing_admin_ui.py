import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class SandboxBillingAdminUITests(unittest.TestCase):
    def test_sandbox_payment_page_exists_and_noindex(self):
        html = (ROOT / "docs" / "payment-sandbox.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex,nofollow"', html)
        self.assertIn("/api/v1/billing/callback?", html)
        self.assertIn("Status=OK", html)

    def test_admin_page_exists_and_uses_server_auth(self):
        html = (ROOT / "docs" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("/api/v1/admin/dashboard", html)
        self.assertIn("/api/v1/admin/users", html)
        self.assertIn("/api/v1/admin/feedback", html)
        self.assertIn("Bearer ", html)
        self.assertIn("admin", html)
        self.assertIn("support", html)

    def test_index_exposes_admin_entry_only_for_admin_roles(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="admin.html"', html)
        self.assertIn("role === 'admin' || role === 'support'", html)

    def test_mock_provider_redirect_is_not_an_invalid_host(self):
        from payment_providers import MockPaymentProvider
        result = MockPaymentProvider().request_payment(
            amount_rial=2_490_000,
            order_public_id="order-test-1",
            callback_url="https://api.asbe-siah.ir/api/v1/billing/callback",
        )
        self.assertTrue(result["payment_url"].startswith("https://asbe-siah.ir/payment-sandbox.html?"))
        self.assertNotIn("example.invalid", result["payment_url"])

    def test_production_sandbox_requires_explicit_approval(self):
        from production_billing_guard import assert_production_billing_configuration
        keys = ["APP_ENV", "BILLING_PROVIDER", "BILLING_SANDBOX_MODE", "BILLING_SANDBOX_APPROVED", "BILLING_FREE_MODE"]
        old = {k: os.environ.get(k) for k in keys}
        try:
            os.environ.update({"APP_ENV": "production", "BILLING_PROVIDER": "mock", "BILLING_SANDBOX_MODE": "true", "BILLING_SANDBOX_APPROVED": "false", "BILLING_FREE_MODE": "false"})
            with self.assertRaises(Exception):
                assert_production_billing_configuration()
            os.environ["BILLING_SANDBOX_APPROVED"] = "true"
            assert_production_billing_configuration()
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
