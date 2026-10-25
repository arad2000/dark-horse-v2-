from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class PwaAuthCacheContractTests(unittest.TestCase):
    def test_canonical_index_excludes_legacy_auth_observer_and_bumps_clients(self):
        index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("profile_auth_cleanup.js", index)
        self.assertIn('auth_api_client.js?v=6', index)
        self.assertIn('commercial_ui.js?v=24', index)
        self.assertIn('password_reset_ui.js?v=4', index)
        self.assertIn('pwa-boot.js?v=62', index)

    def test_service_worker_rotates_cache(self):
        sw = (ROOT / "docs" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("darkhorse-v62", sw)
        self.assertIn("cache: 'no-store'", sw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
