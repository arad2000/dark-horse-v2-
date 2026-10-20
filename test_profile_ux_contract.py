import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "docs" / "profile_ux_v1.js").read_text(encoding="utf-8")
CSS = (ROOT / "docs" / "profile_ux_v1.css").read_text(encoding="utf-8")


class ProfileUXContractTests(unittest.TestCase):
    def test_assets_are_loaded_after_shell_and_commercial_ui(self):
        self.assertIn('profile_ux_v1.css?v=5', HTML)
        shell_pos = HTML.index('src="shell.js?v=88"')
        profile_pos = HTML.index('src="profile_ux_v1.js?v=7"')
        self.assertLess(shell_pos, profile_pos)

    def test_legacy_home_and_exit_removed_and_local_subscription_cleaned(self):
        self.assertIn("'dh-p-home'", JS)
        self.assertIn("'dh-p-prem'", JS)
        self.assertIn("'dh-p-exit'", JS)
        self.assertIn("function removeLegacyProfileControls(card)", JS)
        self.assertIn("function removeLocalSubscriptionState()", JS)

    def test_admin_is_separate_and_uses_server_role(self):
        self.assertIn("function isAdmin(user)", JS)
        self.assertIn("user.is_admin === true || user.role === 'admin'", JS)
        self.assertIn("/api/v1/admin/dashboard", (ROOT / "docs" / "admin.html").read_text(encoding="utf-8"))

    def test_support_links_preserved(self):
        self.assertIn("https://eitaa.com/asbe_siah", JS)

    def test_ui_layer_does_not_touch_quota_or_scoring(self):
        self.assertNotIn("consumeTest(", JS)
        self.assertNotIn("localQuota(", JS)
        self.assertNotIn("saveQuota(", JS)
        self.assertNotIn("displayResults", JS)

    def test_mobile_hierarchy_styles_present(self):
        self.assertIn(".dh-profile-v2", CSS)


if __name__ == "__main__":
    unittest.main()
