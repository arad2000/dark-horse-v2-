"""Static contract checks for the server-authoritative quota state flow."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_commercial_api_exposes_persistent_quota_totals() -> None:
    source = _text("commercial_api.py")
    tree = ast.parse(source)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "_quota_details" in functions
    assert '"credits_consumed"' in source
    assert '"credits_granted"' in source


def test_auth_client_consumes_server_snapshot_instead_of_incrementing_guess() -> None:
    source = _text("docs/auth_api_client.js")
    assert "persistQuotaSnapshot" in source
    assert "credits_consumed" in source
    assert "serverGranted" in source


def test_quota_reconciler_loads_after_auth_and_before_commercial_ui() -> None:
    source = _text("docs/index.html")
    auth_pos = source.index("auth_api_client.js")
    reconciler_pos = source.index("quota_state_reconciler.js")
    commercial_pos = source.index("commercial_ui.js")
    assert auth_pos < reconciler_pos < commercial_pos


def test_pwa_versions_are_aligned() -> None:
    html = _text("docs/index.html")
    boot = _text("docs/pwa-boot.js")
    sw = _text("docs/sw.js")
    assert "pwa-boot.js?v=62" in html
    assert "SW_URL = './sw.js?v=62'" in boot
    assert "darkhorse-v62" in sw


def test_only_one_0008_revision_remains() -> None:
    migration_dir = ROOT / "alembic" / "versions"
    revisions = []
    for path in migration_dir.glob("0008_*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        revision = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "revision" for target in node.targets)
            and isinstance(node.value, ast.Constant)
        )
        revisions.append(revision)
    assert revisions == ["0008_reconciled_operational_schema"]
