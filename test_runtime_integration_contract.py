from pathlib import Path
import re

from main_v2 import app


def test_runtime_routes_are_mounted():
    paths = set(app.openapi()["paths"])
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
    paths = set(app.openapi()["paths"])
    assert "/api/v2/darkhorse/discover" in paths
    assert "/api/v2/darkhorse/branch-discovery" in paths


def test_alembic_chain_is_linear_from_0001_to_0007():
    versions_dir = Path("alembic/versions")
    files = sorted(versions_dir.glob("*.py"))
    revisions = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        revision = re.search(r'^revision\s*=\s*[\"\']([^\"\']+)[\"\']', text, re.MULTILINE)
        down_revision = re.search(r'^down_revision\s*=\s*(None|[\"\']([^\"\']+)[\"\'])', text, re.MULTILINE)
        if revision:
            revisions[revision.group(1)] = None if not down_revision or down_revision.group(1) == "None" else down_revision.group(2)

    expected = [
        "0001_initial_hybrid_schema",
        "0002_auth_billing",
        "0003_credit_based_entitlements",
        "0004_txn_unique",
        "0005_payment_transaction_partial_unique",
        "0006_feedback_submissions",
        "0007_auth_challenges_saved_results",
    ]
    assert list(revisions) == expected
    assert revisions[expected[0]] is None
    for current, previous in zip(expected[1:], expected[:-1]):
        assert revisions[current] == previous
