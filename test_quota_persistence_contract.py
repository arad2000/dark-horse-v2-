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
    assert '"credits_remaining"' in source


def test_consume_test_is_session_idempotent() -> None:
    source = _text("commercial_api.py")
    assert "class ConsumeTestRequest" in source
    assert "session_uuid" in source
    assert "with_for_update()" in source
    assert "JourneyCreditConsumption" in source
    assert "already_consumed" in source
    # Session completion is an independent journey lifecycle state, not the
    # billing idempotency marker. The dedicated ledger owns idempotency.
    assert "session.is_completed" not in source


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
    assert "quota_enforcement_bridge.js" in source
    assert "free_journey_mode.js" not in source


def test_quota_consume_session_adapter_is_loaded_after_bridge() -> None:
    source = _text("docs/index.html")
    bridge_pos = source.index("quota_enforcement_bridge.js")
    adapter_pos = source.index("quota_consume_session_adapter.js")
    commercial_pos = source.index("commercial_ui.js")
    assert bridge_pos < adapter_pos < commercial_pos


def test_quota_bridge_uses_declared_quota_key() -> None:
    source = _text("docs/quota_enforcement_bridge.js")
    assert "var QUOTA_KEY = 'dh_local_quota_v1';" in source
    assert "this.getItem(QUOTA_KEY)" in source
    assert "this.getItem(KEY)" not in source


def test_quota_consume_session_adapter_binds_session_uuid() -> None:
    source = _text("docs/quota_consume_session_adapter.js")
    assert "DHQuotaEnforcement" in source
    assert "ensureJourneySession" in source
    assert "/api/v1/me/consume-test" in source
    assert "session_uuid" in source


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
            node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "revision" for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        revisions.append(revision)
    assert revisions == ["0008_reconciled_schema"]
