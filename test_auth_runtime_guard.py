from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class AuthRuntimeGuardTests(unittest.TestCase):
    def test_no_legacy_profile_observer_in_canonical_entrypoint(self):
        index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("profile_auth_cleanup.js", index)

    def test_auth_client_has_timeout(self):
        content = (ROOT / "docs" / "auth_api_client.js").read_text(encoding="utf-8")
        self.assertIn("REQUEST_TIMEOUT_MS = 15000", content)
        self.assertIn("new AbortController()", content)

    def test_pwa_cache_rotation_is_present(self):
        sw = (ROOT / "docs" / "sw.js").read_text(encoding="utf-8")
        boot = (ROOT / "docs" / "pwa-boot.js").read_text(encoding="utf-8")
        self.assertIn("darkhorse-v62", sw)
        self.assertIn("sw.js?v=62", boot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
