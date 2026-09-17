from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_migration_chain_has_single_0008_and_contiguous_revisions() -> None:
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
    ]

    source = read("alembic/versions/0008_reconciled_operational_schema.py")
    assert 'revision = "0008_reconciled_schema"' in source
    assert 'down_revision = "0007_auth_saved_results"' in source
    assert "user_id" in source
    assert "BigInteger" in source


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


def test_cutover_flags_stay_disabled_in_ci_contract() -> None:
    workflow = read(".github/workflows/hybrid-reconciled-audit.yml")
    assert 'POSTGRES_RUNTIME_CUTOVER_APPROVED: "false"' in workflow
    assert 'DARK_HORSE_SHADOW_PERSISTENCE: "false"' in workflow
