from pathlib import Path
import unittest


class CommercialUIContractTests(unittest.TestCase):
    def setUp(self):
        self.docs = Path(__file__).parent / "docs"
        self.index = (self.docs / "index.html").read_text(encoding="utf-8")
        self.auth = (self.docs / "auth_api_client.js").read_text(encoding="utf-8")
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
        auth_pos = self.index.index('src="auth_api_client.js"')
        ui_pos = self.index.index('src="commercial_ui.js?v=1"')
        self.assertLess(auth_pos, ui_pos)
        self.assertIn("DHAuth.createPayment", self.ui)
        self.assertIn("DHAuth.consumeTest", self.ui)
        self.assertIn("DHAuth.quota", self.ui)

    def test_commercial_ui_removes_legacy_local_only_premium_action(self):
        self.assertIn("خرید بسته ۳ تست", self.ui)
        self.assertIn("#dh-p-prem", self.ui)
        self.assertNotIn("devActivatePremium", self.ui)

    def test_save_result_contract_uses_summary_only(self):
        self.assertIn("async saveResult(summary)", self.auth)
        self.assertIn("await global.DHAuth.saveResult(summary);", self.ui)
        self.assertNotIn("DHAuth.saveResult(sessionId, summary)", self.ui)
        self.assertIn("result_summary: summary || {}", self.auth)
        self.assertIn("session_id: sessionId", self.auth)

    def test_discovery_bridge_propagates_and_persists_session(self):
        self.assertIn("discover|branch-discovery", self.ui)
        self.assertIn("payload.session_id = sessionId", self.ui)
        self.assertIn("journey.sessionId = String(body.session_id)", self.ui)
        self.assertIn("persistFinalResultSummary(body", self.ui)
        self.assertIn("typeof global.DHCommercialUI?.persistFinalResultSummary === 'function'", self.ui)


if __name__ == "__main__":
    unittest.main(verbosity=2)
