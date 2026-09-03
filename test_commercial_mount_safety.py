"""Safety contract: commercial HTTP mount must not enable PostgreSQL cutover."""
from __future__ import annotations

import unittest

import commercial_api
from main_v2 import app
from migration_control import POSTGRES_RUNTIME_CUTOVER_APPROVED, is_postgres_runtime_enabled


EXPECTED_COMMERCIAL_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/me",
    "/api/v1/me/quota",
    "/api/v1/me/consume-test",
    "/api/v1/billing/create-payment",
    "/api/v1/billing/callback",
}

FORBIDDEN_ADMIN_PATHS = {
    "/api/v1/admin/dashboard",
    "/api/v1/admin/credits/grant",
    "/api/v1/admin/entitlements/revoke",
}


class CommercialMountSafetyTests(unittest.TestCase):
    def test_cutover_remains_off(self):
        self.assertIs(POSTGRES_RUNTIME_CUTOVER_APPROVED, False)
        self.assertIs(is_postgres_runtime_enabled(), False)

    def test_scoring_and_commercial_routes_coexist(self):
        paths = {getattr(route, "path", "") for route in app.routes}
        missing = sorted(EXPECTED_COMMERCIAL_PATHS - paths)
        diagnostic = {
            "main_v2": __import__("main_v2").__file__,
            "commercial_api": commercial_api.__file__,
            "commercial_router_paths": sorted(r.path for r in commercial_api.router.routes),
        }
        self.assertFalse(missing, f"commercial routes missing: {missing}; diagnostic={diagnostic}")
        self.assertIn("/api/v2/darkhorse/discover", paths)
        self.assertIn("/api/v2/darkhorse/branch-discovery", paths)

    def test_admin_http_is_not_mounted_on_public_app(self):
        paths = {getattr(route, "path", "") for route in app.routes}
        leaked = sorted(FORBIDDEN_ADMIN_PATHS & paths)
        self.assertFalse(leaked, f"admin routes must stay off main_v2: {leaked}")

    def test_scoring_endpoints_are_not_prefixed_as_billing(self):
        paths = {getattr(route, "path", "") for route in app.routes}
        self.assertNotIn("/api/v2/darkhorse/discover", {p for p in paths if p.startswith("/api/v1/billing")})


if __name__ == "__main__":
    unittest.main(verbosity=2)
