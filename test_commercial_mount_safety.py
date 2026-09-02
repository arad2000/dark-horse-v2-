"""Safety contract: commercial HTTP mount must not enable PostgreSQL cutover."""
from __future__ import annotations

import unittest

from main_v2 import app
from migration_control import POSTGRES_RUNTIME_CUTOVER_APPROVED, is_postgres_runtime_enabled


class CommercialMountSafetyTests(unittest.TestCase):
    def test_cutover_remains_off(self):
        self.assertIs(POSTGRES_RUNTIME_CUTOVER_APPROVED, False)
        self.assertIs(is_postgres_runtime_enabled(), False)

    def test_scoring_and_commercial_routes_coexist(self):
        paths = {getattr(route, "path", "") for route in app.routes}
        self.assertIn("/api/v2/darkhorse/discover", paths)
        self.assertIn("/api/v2/darkhorse/branch-discovery", paths)
        self.assertIn("/api/v1/auth/register", paths)
        self.assertIn("/api/v1/auth/login", paths)
        self.assertIn("/api/v1/me/quota", paths)
        self.assertIn("/api/v1/me/consume-test", paths)
        self.assertIn("/api/v1/billing/create-payment", paths)
        self.assertIn("/api/v1/billing/callback", paths)

    def test_scoring_endpoints_are_not_prefixed_as_billing(self):
        paths = {getattr(route, "path", "") for route in app.routes}
        self.assertNotIn("/api/v2/darkhorse/discover", {p for p in paths if p.startswith("/api/v1/billing")})


if __name__ == "__main__":
    unittest.main(verbosity=2)
