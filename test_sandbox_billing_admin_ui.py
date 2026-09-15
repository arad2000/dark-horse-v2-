import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class SandboxBillingAdminUITests(unittest.TestCase):
    def test_free_and_paid_credit_contract(self):
        from billing_credit_service import FREE_CREDITS, PACK_3_CREDITS
        self.assertEqual(FREE_CREDITS, 1)
        self.assertEqual(PACK_3_CREDITS, 3)

    def test_sandbox_payment_page_exists_and_noindex(self):
        html = (ROOT / "docs" / "payment-sandbox.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex,nofollow"', html)
        self.assertIn("/api/v1/billing/callback?", html)
        self.assertIn("Status=OK", html)
        self.assertIn("window.location.assign(u)", html)
        self.assertNotIn("redirect:'manual'", html)
        self.assertNotIn("fetch(u", html)

    def test_admin_page_exists_and_uses_server_auth(self):
        html = (ROOT / "docs" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("/api/v1/admin/dashboard", html)
        self.assertIn("/api/v1/admin/users", html)
        self.assertIn("/api/v1/admin/feedback", html)
        self.assertIn("Bearer ", html)
        self.assertIn("admin", html)
        self.assertIn("support", html)
        self.assertIn('id="exit-panel"', html)
        self.assertIn("window.location.replace('index.html?logout=1')", html)
        self.assertIn("localStorage.removeItem('dh_auth_v1')", html)

    def test_index_removes_fixed_admin_entry_and_loads_bridge(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="dh-admin-entry"', html)
        self.assertNotIn('href="admin.html"', html)
        self.assertIn("commercial_ui_bridge_v2.js?v=4", html)

    def test_purchase_bridge_converts_legacy_node_to_one_real_purchase_button(self):
        js = (ROOT / "docs" / "commercial_ui_bridge_v2.js").read_text(encoding="utf-8")
        self.assertIn("var legacy = byId('dh-p-prem')", js)
        self.assertIn("legacy.id = 'dh-p-buy'", js)
        self.assertIn("querySelectorAll('#dh-p-buy')", js)
        self.assertIn("purchases[i].remove()", js)
        self.assertIn("data-testid', 'purchase-pack-3'", js)
        self.assertIn("DHAuth.createPayment", js)
        self.assertIn("window.location.assign(payment.payment_url)", js)
        self.assertNotIn("devActivatePremium", js)

    def test_auth_client_has_no_obsolete_direct_credit_activation(self):
        js = (ROOT / "docs" / "auth_api_client.js").read_text(encoding="utf-8")
        self.assertNotIn("devActivatePremium", js)
        self.assertNotIn("/api/v1/billing/dev-activate-premium", js)

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
