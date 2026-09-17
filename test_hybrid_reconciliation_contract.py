from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_migration_chain_has_single_0009_and_contiguous_revisions() -> None:
    versions = sorted((ROOT / "alembic" / "versions").glob("*.py"))
    names = [p.name for p in versions if p.name[:4].isdigit()]
    assert names == [
        "0001_initial_hybrid_schema.py",
        "0002_auth_billing.py",
        "0003_credit_based_entitlements.py",
        "0004_payment_transaction_uniqueness.py",
        "0005_payment_transaction_partial_unique.py",
        "0006_feedback_submissions.py",
        "0007_auth_challenges_saved_results.py",
        "0008_reconciled_operational_schema.py",
        "0009_journey_credit_consumptions.py",
    ]

    source_0008 = read("alembic/versions/0008_reconciled_operational_schema.py")
    assert 'revision = "0008_reconciled_schema"' in source_0008
    assert 'down_revision = "0007_auth_saved_results"' in source_0008

    source_0009 = read("alembic/versions/0009_journey_credit_consumptions.py")
    assert 'revision = "0009_journey_credit_consumptions"' in source_0009
    assert 'down_revision = "0008_reconciled_schema"' in source_0009
    assert "journey_credit_consumptions" in source_0009
    assert "uq_journey_credit_consumption_session" in source_0009


def test_main_runtime_import_graph_exists() -> None:
    tree = ast.parse(read("main_v2.py"), filename="main_v2.py")
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "admin_http_router" in imports
    assert "commercial_api" in imports
    assert "feedback_api" in imports
    assert (ROOT / "admin_http_router.py").is_file()
    assert (ROOT / "feedback_api.py").is_file()
    assert (ROOT / "feedback_models.py").is_file()


def test_shared_engine_is_initialized_once_per_process() -> None:
    source = read("main_v2.py")
    assert source.count("DarkHorseEngineV2(") == 1
    assert "shared_engine = DarkHorseEngineV2(" in source
    assert "app.state.engine = shared_engine" in source
    assert "app.state.branch_engine = shared_engine" in source


def test_cutover_flags_stay_disabled_in_ci_contract() -> None:
    workflow = read(".github/workflows/hybrid-reconciled-audit.yml")
    assert 'POSTGRES_RUNTIME_CUTOVER_APPROVED: "false"' in workflow
    assert 'DARK_HORSE_SHADOW_PERSISTENCE: "false"' in workflow


def test_frontend_quota_contract_has_one_canonical_charge_path() -> None:
    index = read("docs/index.html")
    ui = read("docs/commercial_ui.js")
    auth = read("docs/auth_api_client.js")
    bridge = read("docs/quota_enforcement_bridge.js")
    reconciler = read("docs/quota_state_reconciler.js")
    session_boot = read("docs/journey_session_boot.js")
    failure_ui = read("docs/quota_charge_failure_ui.js")

    assert 'auth_api_client.js?v=9' in index
    assert 'quota_state_reconciler.js?v=4' in index
    assert 'quota_enforcement_bridge.js?v=3' in index
    assert 'journey_session_boot.js?v=1' in index
    assert 'quota_charge_failure_ui.js?v=1' in index
    assert 'commercial_ui.js?v=28' in index

    assert 'DHAuth.consumeTest' not in ui
    assert 'setLocalQuota({remaining:r-1})' not in ui
    assert 'used:0' not in ui.replace('used: 0', 'used:0')
    assert 'credits_consumed' in auth
    assert 'session_uuid' in auth
    assert 'session_uuid' in bridge
    assert 'consumeForJourney(String(sid2))' in bridge
    assert 'SESSION_MEMORY = uuid();' in bridge
    assert 'serverConsumed' in reconciler
    assert 'ensureAfterStart' in session_boot
    assert 'quota/consume-test' not in failure_ui or '/api/v1/me/consume-test' in failure_ui
    assert 'تلاش دوباره' in failure_ui


def test_audit_runs_p0_quota_regression() -> None:
    workflow = read(".github/workflows/hybrid-reconciled-audit.yml")
    assert "test_p0_quota_consumption.py" in workflow
