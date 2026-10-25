import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class ReleaseHotfixContractTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_registration_client_has_verify_step(self):
        source = self.read("docs/auth_api_client.js")
        self.assertIn("/api/v1/auth/register/verify", source)
        self.assertIn("verifyRegistration", source)

    def test_index_loads_auth_hotfix_after_auth_modules(self):
        source = self.read("docs/index.html")
        self.assertIn('auth_api_client.js?v=2', source)
        self.assertIn('password_reset_ui.js?v=2', source)
        self.assertIn('auth_ui_hotfix.js?v=1', source)

    def test_admin_logout_clears_client_session(self):
        source = self.read("docs/admin.html")
        self.assertIn("localStorage.removeItem('dh_auth_v1')", source)
        self.assertIn("localStorage.removeItem('dh_local_user_v1')", source)
        self.assertIn("index.html?logout=1", source)

    def test_production_free_only_still_allows_controlled_sandbox_provider(self):
        source = self.read("commercial_api.py")
        self.assertNotIn("commercial payment is not activated yet; your free test remains available", source)
        self.assertIn("create_payment_request(", source)
        self.assertIn("provider_name=provider", source)

    def test_sandbox_pack_is_enabled_by_followup_migration(self):
        source = self.read("alembic/versions/0009_enable_sandbox_pack.py")
        self.assertIn("pack_3_tests", source)
        self.assertIn("is_active = TRUE", source)

    def test_purchase_ui_has_singleton_runtime_guard(self):
        source = self.read("docs/auth_ui_hotfix.js")
        self.assertIn("dedupePurchaseButtons", source)
        self.assertIn("خرید بسته ۳ تست", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
