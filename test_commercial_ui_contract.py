from pathlib import Path
import unittest


class CommercialUIContractTests(unittest.TestCase):
    def setUp(self):
        self.docs = Path(__file__).parent / "docs"
        self.index = (self.docs / "index.html").read_text(encoding="utf-8")
        self.auth = (self.docs / "auth_api_client.js").read_text(encoding="utf-8")
        self.ui = (self.docs / "commercial_ui.js").read_text(encoding="utf-8")
        self.app = (self.docs / "app.js").read_text(encoding="utf-8")

    def test_liara_is_canonical_frontend_backend(self):
        self.assertIn("https://asbe-siah.liara.run", self.app)
        self.assertIn("https://asbe-siah.liara.run", self.auth)
        self.assertNotIn("dark-horse-v2.onrender.com", self.auth)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
