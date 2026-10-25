from pathlib import Path
import re
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
        ]
        for optional_name in ("quota_runtime.js", "purchase_ui_fix.js", "auth_runtime_guard.js"):
            candidate = DOCS / optional_name
            if candidate.exists():
                scripts.append(candidate)

        for path in scripts:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"Syntax error in {path}: {result.stderr}")

        index = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertRegex(index, r'src="auth_api_client\.js\?v=[^"]+"')
        self.assertRegex(index, r'src="shell\.js\?v=[^"]+"')
        self.assertRegex(index, r'src="commercial_ui\.js\?v=[^"]+"')
        self.assertRegex(index, r'src="password_reset_ui\.js\?v=[^"]+"')
        self.assertNotIn("profile_auth_cleanup.js", index)
        self.assertNotIn("commercial_ui_bridge_v2.js", index)
        self.assertNotIn("auth_ui_hotfix.js", index)
        self.assertNotIn("commercial_ui_bridge_v3.js", index)

    def test_canonical_auth_and_logout_contract(self):
        auth = (DOCS / "auth_api_client.js").read_text(encoding="utf-8")
        source = (DOCS / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertIn("logout()", auth)
        self.assertIn("global.DHAuth.register", source)
        self.assertIn("global.DHAuth.verifyRegistration", source)
        self.assertIn("global.DHAuth.login", source)
        self.assertIn("DHAuth.logout", source)
        self.assertIn("DHAuth.createPayment", source)
        self.assertIn("dh_auth_v1", source)
        self.assertIn("logout: doLogout", source)
        self.assertIn("global.DHCommercialUI =", source)
        self.assertNotIn("global.DHCommercialUIglobal", source)
        self.assertNotIn("devActivatePremium", source)
        self.assertIn("dh-p-buy", source)
        self.assertIn("AndroidBridge.openExternalUrl", source)

    def test_password_reset_is_single_secondary_action(self):
        source = (DOCS / "password_reset_ui.js").read_text(encoding="utf-8")
        self.assertIn("DHAuth.requestPasswordReset", source)
        self.assertIn("DHAuth.resetPassword", source)
        self.assertIn("dh-forgot-password", source)

    def test_no_legacy_local_profile_path_in_runtime_contract(self):
        index = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("profile-tab-guard.js", index)
        self.assertNotIn("profile_runtime_lock.js", index)
        self.assertNotIn("shell_boot_stabilizer.js", index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
