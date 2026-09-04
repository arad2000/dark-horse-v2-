from main_v2 import app


def _paths(routes):
    paths = set()
    for route in routes:
        path = getattr(route, "path", None)
        if path:
            paths.add(path)
        nested = getattr(route, "routes", None)
        if nested:
            paths.update(_paths(nested))
    return paths


def test_runtime_routes_are_mounted():
    paths = _paths(app.routes)
    expected = {
        "/api/v1/auth/register",
        "/api/v1/auth/register/verify",
        "/api/v1/auth/login",
        "/api/v1/me",
        "/api/v1/me/quota",
        "/api/v1/me/consume-test",
        "/api/v1/me/save-result",
        "/api/v1/billing/create-payment",
        "/api/v1/billing/callback",
        "/api/v1/feedback",
        "/api/v1/admin/dashboard",
        "/api/v1/admin/users",
        "/api/v1/admin/feedback",
        "/api/v1/admin/credits/grant",
        "/api/v1/admin/entitlements/revoke",
        "/api/v2/darkhorse/discover",
        "/api/v2/darkhorse/branch-discovery",
    }
    assert expected <= paths


def test_scoring_routes_remain_present():
    paths = _paths(app.routes)
    assert "/api/v2/darkhorse/discover" in paths
    assert "/api/v2/darkhorse/branch-discovery" in paths
