import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class FrontendBillingAdminSandboxContractTests(unittest.TestCase):
    def test_bridge_converts_legacy_dom_node_and_removes_duplicates(self):
        profile_js = (DOCS / "profile_ux_v1.js").read_text(encoding="utf-8")
        purchase_js = (DOCS / "commercial_ui.js").read_text(encoding="utf-8") + "\n" + (DOCS / "shell.js").read_text(encoding="utf-8")
        self.assertIn("'dh-p-prem'", profile_js)
        self.assertIn("خرید بسته ۳ تست", purchase_js)

    def test_bridge_never_recreates_a_second_purchase_button(self):
        purchase_js = (DOCS / "commercial_ui.js").read_text(encoding="utf-8") + "\n" + (DOCS / "shell.js").read_text(encoding="utf-8")
        self.assertIn("dh-p-buy", purchase_js)

    def test_fixed_home_admin_entry_is_removed_at_runtime(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="dh-admin-entry"', html)
        self.assertNotIn('href="admin.html"', html)

    def test_admin_panel_has_explicit_exit_control(self):
        html = (DOCS / "admin.html").read_text(encoding="utf-8")
        self.assertIn('id="exit-panel"', html)
        self.assertIn("خروج از پنل", html)
        self.assertIn("window.location.assign('index.html')", html)

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
