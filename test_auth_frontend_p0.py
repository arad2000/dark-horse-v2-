from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class AuthFrontendP0ContractTests(unittest.TestCase):
    def test_auth_client_has_bounded_requests(self):
        content = (ROOT / "docs" / "auth_api_client.js").read_text(encoding="utf-8")
        self.assertIn("REQUEST_TIMEOUT_MS = 15000", content)
        self.assertIn("new AbortController()", content)
        self.assertIn("زمان پاسخ سرور تمام شد", content)

    def test_auth_ui_does_not_start_background_quota_poll(self):
        content = (ROOT / "docs" / "commercial_ui.js").read_text(encoding="utf-8")
        self.assertIn("QUOTA_MIN_INTERVAL_MS = 10000", content)
        self.assertIn("QUOTA_SYNC_IN_FLIGHT", content)
        self.assertIn("No background quota request on page boot", content)
        self.assertNotIn("syncQuota(function () {})", content)

    def test_auth_entrypoints_are_single_server_paths(self):
        index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(index.count('src="auth_api_client.js?v=5"'), 1)
        self.assertEqual(index.count('src="commercial_ui.js?v=23"'), 1)
        self.assertEqual(index.count('src="password_reset_ui.js?v=3"'), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
