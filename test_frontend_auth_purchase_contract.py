from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class FrontendAuthPurchaseContractTests(unittest.TestCase):
    def test_script_syntax_and_canonical_script_set(self):
        scripts = [
            DOCS / "auth_api_client.js",
            DOCS / "shell.js",
            DOCS / "commercial_ui.js",
            DOCS / "password_reset_ui.js",
            DOCS / "profile_auth_cleanup.js",
        ]
        for path in scripts:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"Syntax error in {path}: {result.stderr}")

        index = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn('auth_api_client.js?v=5', index)
        self.assertIn('shell.js?v=60', index)
        self.assertIn('commercial_ui.js?v=23', index)
        self.assertIn('password_reset_ui.js?v=3', index)
        self.assertIn('profile_auth_cleanup.js?v=1', index)
        self.assertNotIn('commercial_ui_bridge_v2.js', index)
        self.assertNotIn('auth_ui_hotfix.js', index)
        self.assertNotIn('commercial_ui_bridge_v3.js', index)

    def test_canonical_auth_and_logout_contract(self):
        source = (DOCS / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertIn("global.DHAuth.register", source)
        self.assertIn("global.DHAuth.verifyRegistration", source)
        self.assertIn("global.DHAuth.login", source)
        self.assertIn("DHAuth.logout", source)
        self.assertIn("dh_auth_v1", source)
        self.assertIn("logout: doLogout", source)
        self.assertIn("global.DHCommercialUI =", source)
        self.assertNotIn("global.DHCommercialUIglobal", source)
        self.assertIn("dh-p-buy", source)
        self.assertIn("AndroidBridge.openExternalUrl", source)

    def test_password_reset_is_single_secondary_action(self):
        source = (DOCS / "password_reset_ui.js").read_text(encoding="utf-8")
        self.assertIn("DHAuth.requestPasswordReset", source)
        self.assertIn("DHAuth.resetPassword", source)
        self.assertIn("dh-forgot-password", source)
        self.assertIn('autocomplete="new-password"', source)

    def test_cleanup_does_not_create_parallel_buttons_or_auth_flows(self):
        source = (DOCS / "profile_auth_cleanup.js").read_text(encoding="utf-8")
        self.assertIn("dh-p-register", source)
        self.assertIn("dh-p-login", source)
        self.assertIn("dh-p-buy", source)
        self.assertIn("dh-p-prem", source)
        self.assertIn("dh-p-save", source)
        self.assertNotIn("createElement('button')", source)
        self.assertNotIn('createElement("button")', source)
        self.assertNotIn("DHAuth.register", source)
        self.assertNotIn("DHAuth.login", source)
        self.assertNotIn("DHAuth.createPayment", source)

    def test_no_legacy_local_profile_path_in_runtime_contract(self):
        shell = (DOCS / "shell.js").read_text(encoding="utf-8")
        cleanup = (DOCS / "profile_auth_cleanup.js").read_text(encoding="utf-8")
        self.assertIn("dh-p-save", shell)
        self.assertIn("removeLegacyGuestFields", cleanup)
        self.assertIn("dh-p-prem", cleanup)
        self.assertIn("خرید بسته ۳ تست", cleanup)


if __name__ == "__main__":
    unittest.main(verbosity=2)
