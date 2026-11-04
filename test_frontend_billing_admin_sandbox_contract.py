import unittest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class FrontendBillingAdminSandboxContractTests(unittest.TestCase):
    def test_bridge_converts_legacy_dom_node_and_removes_duplicates(self):
        js = (DOCS / "commercial_ui_bridge_v2.js").read_text(encoding="utf-8")
        self.assertIn("var legacy = byId('dh-p-prem')", js)
        self.assertIn("legacy.id = 'dh-p-buy'", js)
        self.assertIn("purchases[i].remove()", js)
        self.assertIn("خرید بسته ۳ تست", js)
        self.assertIn("window.location.assign(payment.payment_url)", js)

    def test_bridge_never_recreates_a_second_purchase_button(self):
        js = (DOCS / "commercial_ui_bridge_v2.js").read_text(encoding="utf-8")
        self.assertEqual(js.count("createElement('button')"), 1)
        self.assertNotIn("createElement('button').id = 'dh-p-buy'", js)
        self.assertIn("querySelectorAll('#dh-p-buy')", js)

    def test_fixed_home_admin_entry_is_removed_at_runtime(self):
        js = (DOCS / "commercial_ui_bridge_v2.js").read_text(encoding="utf-8")
        self.assertIn("var fixedEntry = byId('dh-admin-entry')", js)
        self.assertIn("fixedEntry.remove()", js)
        self.assertIn("dh-profile-admin-entry", js)
        self.assertIn("admin.html", js)

    def test_admin_panel_has_explicit_exit_control(self):
        html = (DOCS / "admin.html").read_text(encoding="utf-8")
        self.assertIn('id="exit-panel"', html)
        # Contract: docs/admin.html exit-panel onclick (64fc2a94) and
        # SandboxBillingAdminUITests: clear session/local state, replace to logout=1.
        self.assertRegex(html, r'<button\b[^>]*id="exit-panel"[^>]*>\s*خروج از حساب\s*</button>')
        handler = re.search(
            r"document\.getElementById\('exit-panel'\)\.onclick=function\(\)\{(.*?)\n\};",
            html, re.S,
        )
        self.assertIsNotNone(handler, "Exit button must have a logout handler")
        logout = handler.group(1)
        redirect = "window.location.replace('index.html?logout=1')"
        self.assertIn(redirect, logout)
        for key in ("dh_auth_v1", "dh_local_user_v1", "dh_local_quota_v1"):
            clear = "localStorage.removeItem('" + key + "')"
            self.assertIn(clear, logout)
            self.assertLess(logout.index(clear), logout.index(redirect))

    def test_legacy_offline_label_is_absent_from_static_docs(self):
        legacy_labels = (
            "اشتراک محلی آفلاین",
            "اشتراک محلی آفلاین (تست)",
        )
        for path in DOCS.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".html", ".js", ".css"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for label in legacy_labels:
                    self.assertNotIn(label, text, msg=f"legacy label found in {path}")


if __name__ == "__main__":
    unittest.main()
