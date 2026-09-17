from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
INDEX = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "docs" / "profile_ux_v1.js").read_text(encoding="utf-8")
CSS = (ROOT / "docs" / "profile_ux_v1.css").read_text(encoding="utf-8")


class ProfileUXContractTests(unittest.TestCase):
    def test_assets_are_loaded_after_shell_and_commercial_ui(self):
        self.assertIn('profile_ux_v1.css?v=1', INDEX)
        shell_pos = INDEX.index('shell.js?v=62')
        commercial_pos = INDEX.index('commercial_ui.js?v=24')
        ux_pos = INDEX.index('profile_ux_v1.js?v=1')
        self.assertLess(shell_pos, ux_pos)
        self.assertLess(commercial_pos, ux_pos)

    def test_profile_order_and_primary_cta(self):
        render = JS[JS.index("wrap.innerHTML = ''"):]
        order = [
            'dh-profile-header',
            'dh-profile-stats',
            'dh-profile-last',
            'dh-profile-actions',
            'dh-support-card',
            'dh-profile-account',
            'dh-admin-panel',
        ]
        positions = [render.index("className = '" + name + "'") for name in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("journey.classList.add('dh-profile-journey')", JS)
        self.assertIn("buy.className = 'btn dh-profile-buy'", JS)
        self.assertNotIn("buy.className = 'btn btn-primary", JS)

    def test_legacy_home_and_exit_removed_and_test_subscription_debug_only(self):
        self.assertIn("card.querySelector('#dh-p-home')", JS)
        self.assertIn("card.querySelector('#dh-p-exit')", JS)
        self.assertIn("function stripGuestLegacyProfileControls()", JS)
        self.assertIn("global.__DH_DEBUG__ === true", JS)
        self.assertIn("'اشتراک محلی آفلاین (تست)'", JS)
        self.assertIn("else if (legacyPrem) {\n      legacyPrem.remove();", JS)

    def test_share_only_when_result_exists(self):
        self.assertIn("var hasResult = !!(last && !last.classList.contains('dh-last-empty'));", JS)
        self.assertIn("if (hasResult && share)", JS)
        self.assertIn("} else if (share) {\n      share.remove();", JS)
        self.assertIn("if (hasResult) {", JS)
        self.assertIn("} else if (last) {\n      last.remove();", JS)

    def test_admin_is_separate_and_read_only_metrics(self):
        self.assertIn("function isAdmin(user)", JS)
        self.assertIn("user.is_admin === true || user.role === 'admin'", JS)
        self.assertIn("data-admin-metric=\"users\"", JS)
        self.assertIn("data-admin-metric=\"feedback\"", JS)
        self.assertIn("data-admin-metric=\"payments\"", JS)
        self.assertIn("/api/v1/admin/dashboard", JS)

    def test_support_links_and_shell_scroll(self):
        self.assertIn('https://eitaa.com/', JS)
        self.assertIn('https://enamad.ir/', JS)
        self.assertIn('#dh-privacy-note', JS)
        self.assertIn('global.shellScrollTop', JS)
        self.assertIn('scroller.scrollTop = 0', JS)

    def test_ui_layer_does_not_touch_quota_or_scoring(self):
        self.assertNotIn('consumeTest(', JS)
        self.assertNotIn('localQuota(', JS)
        self.assertNotIn('saveQuota(', JS)
        self.assertNotIn('displayResults', JS)
        self.assertNotIn('state.', JS)

    def test_mobile_hierarchy_is_compact(self):
        for token in ('gap: 8px', 'margin: 0 0 12px', 'font-size: .77rem', 'grid-template-columns: repeat(3'):
            self.assertIn(token, CSS)
        self.assertIn('.dh-profile-actions .dh-profile-share', CSS)
        self.assertIn('.dh-profile-account .btn', CSS)


if __name__ == '__main__':
    unittest.main()
