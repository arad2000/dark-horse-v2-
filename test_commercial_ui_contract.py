from pathlib import Path
import unittest


class CommercialUIContractTests(unittest.TestCase):
    def setUp(self):
        self.docs = Path(__file__).parent / "docs"
        self.index = (self.docs / "index.html").read_text(encoding="utf-8")
        self.auth = (self.docs / "auth_api_client.js").read_text(encoding="utf-8")
        self.quota_rt = (self.docs / "quota_runtime.js").read_text(encoding="utf-8")
        self.ui = (self.docs / "commercial_ui.js").read_text(encoding="utf-8")
        self.app = (self.docs / "app.js").read_text(encoding="utf-8")

    def test_canonical_frontend_backend_domain(self):
        self.assertIn("https://api.asbe-siah.ir", self.app)
        self.assertIn("https://api.asbe-siah.ir", self.auth)
        self.assertNotIn("dark-horse-v2.onrender.com", self.auth)
        self.assertNotIn("https://asbe-siah.liara.run", self.app)
        self.assertNotIn("https://asbe-siah.liara.run", self.auth)

    def test_auth_client_exposes_server_authoritative_billing(self):
        for marker in (
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/me/quota",
            "/api/v1/me/consume-test",
            "/api/v1/billing/create-payment",
        ):
            self.assertIn(marker, self.auth)

    def test_commercial_ui_is_loaded_after_auth_client(self):
        auth_pos = self.index.index('src="auth_api_client.js?v=10"')
        quota_pos = self.index.index('src="quota_runtime.js?v=4"')
        ui_pos = self.index.index('src="commercial_ui.js?v=46"')
        self.assertLess(auth_pos, quota_pos)
        self.assertLess(quota_pos, ui_pos)
        self.assertIn("DHAuth.createPayment", self.ui)
        self.assertIn("DHAuth.consumeTest", self.quota_rt)
        self.assertIn("DHAuth.quota", self.ui)

    def test_commercial_ui_removes_legacy_local_only_premium_action(self):
        self.assertIn("خرید بسته ۳ تست", self.ui)
        self.assertNotIn("فعال‌سازی اشتراک", self.ui)
        self.assertNotIn("devActivatePremium", self.ui)

    def test_save_result_contract_uses_session_uuid(self):
        self.assertIn("saveResult(", self.auth)
        self.assertIn("result_summary:", self.auth)
        self.assertIn("session_uuid:", self.auth)

    def test_discovery_bridge_propagates_and_persists_session(self):
        self.assertIn("DHQuotaEnforcement.consumeForJourney", self.ui)
        self.assertIn("session_id", self.app)
        self.assertIn("saveResult", self.auth)


if __name__ == "__main__":
    unittest.main(verbosity=2)
