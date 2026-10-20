from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class FrontendAuthPurchaseContractTests(unittest.TestCase):
    def test_script_syntax_and_canonical_script_set(self):
        scripts = [
            DOCS / "auth_api_client.js",
            DOCS / "quota_state_reconciler.js",
            DOCS / "shell_runtime_fix.js",
            DOCS / "shell.js",
            DOCS / "quota_runtime.js",
            DOCS / "commercial_ui.js",
            DOCS / "purchase_ui_fix.js",
            DOCS / "password_reset_ui.js",
        ]
        for path in scripts:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"Syntax error in {path}: {result.stderr}")

        index = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn('auth_api_client.js?v=10', index)
        self.assertIn('shell.js?v=88', index)
        self.assertIn('quota_runtime.js?v=4', index)
        self.assertIn('commercial_ui.js?v=46', index)
        self.assertIn('purchase_ui_fix.js?v=11', index)
        self.assertIn('password_reset_ui.js?v=1', index)

    def test_canonical_auth_and_logout_contract(self):
        auth = (DOCS / "auth_api_client.js").read_text(encoding="utf-8")
        ui = (DOCS / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertIn("logout()", auth)
        self.assertIn("DHAuth.createPayment", ui)
        self.assertNotIn("devActivatePremium", ui)

    def test_no_legacy_local_profile_path_in_runtime_contract(self):
        index = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("profile_auth_cleanup.js", index)
        self.assertNotIn("commercial_ui_bridge_v2.js", index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
