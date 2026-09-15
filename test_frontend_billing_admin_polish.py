import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class FrontendBillingAdminPolishTests(unittest.TestCase):
    def test_shell_has_one_commercial_purchase_button(self):
        html = (DOCS / "shell.js").read_text(encoding="utf-8")
        self.assertIn('id=\"dh-p-buy\"', html)
        self.assertIn('id=\"dh-p-prem\"', html)
        # The legacy offline premium control is removed at runtime by the bridge;
        # there must not be a second commercial purchase id.
        self.assertEqual(html.count('id=\"dh-p-buy\"'), 1)

    def test_bridge_removes_legacy_duplicate_and_binds_real_purchase(self):
        js = (DOCS / "commercial_ui_bridge_v2.js").read_text(encoding="utf-8")
        self.assertIn("var legacy = byId('dh-p-prem')", js)
        self.assertIn("legacy.remove()", js)
        self.assertIn("var purchase = byId('dh-p-buy')", js)
        self.assertIn("DHAuth.createPayment", js)
        self.assertIn("window.location.assign(payment.payment_url)", js)

    def test_bridge_places_admin_entry_after_purchase_button(self):
        js = (DOCS / "commercial_ui_bridge_v2.js").read_text(encoding="utf-8")
        self.assertIn("dh-profile-admin-entry", js)
        self.assertIn("purchase.parentNode.insertBefore(btn, purchase.nextSibling)", js)
        self.assertIn("role === 'admin' || role === 'support'", js)

    def test_admin_panel_has_exit_control(self):
        html = (DOCS / "admin.html").read_text(encoding="utf-8")
        self.assertIn('id=\"exit-panel\"', html)
        self.assertIn('خروج از پنل', html)
        self.assertIn("window.location.assign('index.html')", html)

    def test_admin_entry_is_not_a_fixed_home_page_element(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id=\"dh-admin-entry\"', html)
        self.assertIn('commercial_ui_bridge_v2.js?v=3', html)


if __name__ == "__main__":
    unittest.main()
