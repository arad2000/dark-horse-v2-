import unittest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class FrontendBillingAdminSandboxContractTests(unittest.TestCase):
    def test_current_profile_replaces_legacy_purchase_with_single_server_action(self):
        # Contract: docs/index.html loads profile_ux_v1.js + commercial_ui.js;
        # reflowProfile replaces the old card, makeBuyButton delegates to showPurchase.
        index = (DOCS / "index.html").read_text(encoding="utf-8")
        profile = (DOCS / "profile_ux_v1.js").read_text(encoding="utf-8")
        commercial = (DOCS / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertEqual(index.count('src="profile_ux_v1.js?v=1"'), 1)
        self.assertEqual(index.count('src="commercial_ui.js?v=24"'), 1)
        for retired in ("commercial_ui_bridge_v2.js", "commercial_ui_bridge_v3.js", "auth_ui_hotfix.js"):
            self.assertNotIn(retired, index)
        self.assertIn("var legacyPrem = card.querySelector('#dh-p-prem')", profile)
        self.assertRegex(profile, r"else if \(legacyPrem\)\s*\{\s*legacyPrem\.remove\(\);")
        self.assertIn("wrap.innerHTML = '';", profile)
        self.assertLess(profile.index("wrap.innerHTML = '';"), profile.index("wrap.appendChild(shell)"))
        self.assertEqual(profile.count("buy.id = 'dh-p-buy'"), 1)
        self.assertIn("buy.setAttribute('data-testid', 'purchase-pack-3')", profile)
        self.assertIn("buy.textContent = 'خرید بسته ۳ تست'", profile)
        self.assertIn("global.DHCommercialUI.showPurchase();", profile)
        self.assertIn("showPurchase: openPurchaseModal", commercial)
        self.assertIn("await global.DHAuth.createPayment()", commercial)
        self.assertIn("openExternalPay(payment.payment_url)", commercial)
        self.assertIn("window.location.assign(target)", commercial)

    def test_current_purchase_owner_and_hooks_are_idempotent(self):
        # Contract: profile_ux_v1.js owns one purchase node and guards reflow/install;
        # commercial_ui.js hooks the existing node once rather than creating another.
        profile = (DOCS / "profile_ux_v1.js").read_text(encoding="utf-8")
        commercial = (DOCS / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertEqual(profile.count("actions.appendChild(makeBuyButton());"), 1)
        self.assertEqual(profile.count("makeBuyButton()"), 2)  # Definition + sole call.
        self.assertIn("if (!wrap || !card || wrap.querySelector('.dh-profile-v2')) return;", profile)
        self.assertIn("if (INSTALLED) return;", profile)
        self.assertIn("if (WRAPPED) return;", profile)
        self.assertIn("WRAPPED = true;", profile)
        self.assertIn("global.__dhProfileUxObserverInstalled", profile)
        self.assertIn("global.__dhProfileUxObserverInstalled = true;", profile)
        self.assertIn("var buy = el('dh-p-buy');", commercial)
        self.assertIn("if (buy && !buy.__dhCommercialHooked)", commercial)
        self.assertIn("buy.__dhCommercialHooked = true;", commercial)
        self.assertNotIn("createElement('button')", commercial)
        self.assertNotRegex(commercial, r"\.id\s*=\s*['\"]dh-p-buy['\"]")

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
