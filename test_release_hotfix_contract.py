import unittest
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class ReleaseHotfixContractTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_registration_client_has_verify_step(self):
        source = self.read("docs/auth_api_client.js")
        self.assertIn("/api/v1/auth/register/verify", source)
        self.assertIn("verifyRegistration", source)

    def test_index_loads_current_auth_modules_without_legacy_hotfix(self):
        # Contract: docs/index.html + FrontendAuthPurchaseContractTests:
        # current deferred auth/reset/commercial modules, no legacy auth_ui_hotfix.
        source = self.read("docs/index.html")
        scripts = re.findall(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*>', source)
        expected = (
            "auth_api_client.js?v=7", "commercial_ui.js?v=24",
            "password_reset_ui.js?v=4", "auth_runtime_guard.js?v=1",
        )
        for src in expected:
            with self.subTest(script=src):
                name = src.split("?")[0]
                self.assertEqual([s for s in scripts if s.split("?")[0] == name], [src])
                self.assertRegex(source, r'<script\s+defer\s+src="' + re.escape(src) + r'"')
        self.assertTrue(all(src in scripts for src in expected), "All current auth modules must be loaded")
        positions = [scripts.index(src) for src in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("auth_ui_hotfix.js", source)
        self.assertNotIn("commercial_ui_bridge_v2.js", source)
        self.assertNotIn("commercial_ui_bridge_v3.js", source)

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
