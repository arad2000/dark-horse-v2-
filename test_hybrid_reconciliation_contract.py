from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_migration_chain_is_single_and_contiguous() -> None:
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
        "0010_entitlement_order_uniqueness.py",
    ]

    source_0008 = read("alembic/versions/0008_reconciled_operational_schema.py")
    assert 'revision = "0008_reconciled_schema"' in source_0008
    assert 'down_revision = "0007_auth_saved_results"' in source_0008

    source_0009 = read("alembic/versions/0009_journey_credit_consumptions.py")
    assert 'revision = "0009_journey_credit_consumptions"' in source_0009
    assert 'down_revision = "0008_reconciled_schema"' in source_0009
    assert "journey_credit_consumptions" in source_0009
    assert "uq_journey_credit_consumption_session" in source_0009

    source_0010 = read("alembic/versions/0010_entitlement_order_uniqueness.py")
    assert 'revision = "0010_entitlement_order_uniqueness"' in source_0010
    assert 'down_revision = "0009_journey_credit_consumptions"' in source_0010
    assert 'op.create_unique_constraint("uq_entitlement_order"' in source_0010


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


def test_persistence_prefetches_reference_rows_without_n_plus_one() -> None:
    source = read("operational_store.py")
    assert "select(Major.id).where(Major.id.in_(major_ids))" in source
    assert "db.get(Major, major_id)" not in source
    assert "select(SchoolBranch).where(SchoolBranch.name.in_(branch_names))" in source
    assert "db.query(SchoolBranch).all()" not in source


def test_auth_quota_scale_path_uses_single_lookup_and_sql_aggregate() -> None:
    auth = read("auth_service.py")
    commercial = read("commercial_api.py")
    assert "select(AuthSession, User)" in auth
    assert "db.get(User, session.user_id)" not in auth
    assert "func.coalesce(func.sum(Entitlement.credits_granted), 0)" in commercial
    assert "list(db.scalars(select(Entitlement)" not in commercial
    ledger_probe = 'select(JourneyCreditConsumption).where(JourneyCreditConsumption.session_uuid == req.session_uuid)'
    assert commercial.count(ledger_probe) >= 2
    assert commercial.index(ledger_probe) < commercial.index('select(User).where(User.id == user.id).with_for_update()')
    lock_pos = commercial.index('select(User).where(User.id == user.id).with_for_update()')
    recheck_pos = commercial.index(ledger_probe, lock_pos)
    session_lock_pos = commercial.index('select(UserSession).where(UserSession.session_uuid == req.session_uuid).with_for_update()')
    assert recheck_pos < session_lock_pos
    newline = chr(10)
    assert ("details = _quota_details(db, user.id)" + newline + "            db.rollback()" + newline + "            logger.info(\"quota consume idempotent user_id=%s") in commercial
    assert ("details = _quota_details(db, user.id)" + newline + "            db.rollback()" + newline + "            logger.info(\"quota consume idempotent-after-lock user_id=%s") in commercial

    billing_models = read("billing_models.py")
    assert 'UniqueConstraint("order_id", name="uq_entitlement_order")' in billing_models

    credit = read("billing_credit_service.py")
    assert "update(Entitlement)" in credit
    assert ".returning(Entitlement)" in credit
    assert "scalar_one_or_none()" in credit
    assert "Entitlement.credits_remaining > 0" in credit


def test_staging_load_workflow_blocks_production_targets_and_limits_probe() -> None:
    workflow = read(".github/workflows/scale-baseline.yml")
    assert "production load testing is blocked by CI safety guard" in workflow
    assert '"api.asbe-siah.ir"' in workflow
    assert '"www.asbe-siah.ir"' in workflow
    assert '"asbe-siah.ir"' in workflow
    assert '"REQUESTS": (1, 5000)' in workflow
    assert '"CONCURRENCY": (1, 100)' in workflow


def test_multireplica_scale_workflow_is_paired_on_one_runner() -> None:
    workflow = read(".github/workflows/multireplica-db-scale.yml")
    assert "runs-on: ubuntu-latest" in workflow
    assert 'SCALE_TRIALS: "3"' in workflow
    assert "for replicas in 1 2 3;" in workflow
    assert '"postgres_instance": "single per workflow"' in workflow
    assert 'trials_per_replica_count' in workflow
    assert "matrix:" not in workflow
    assert "multireplica-summary.json" in workflow


def test_payment_verification_serializes_concurrent_callbacks() -> None:
    source = read("billing_credit_service.py")
    lock_expr = 'select(Payment).where(Payment.id == payment_public_id).with_for_update()'
    assert lock_expr in source
    assert source.index(lock_expr) < source.index('if payment.status == "verified":')
    free_lock = 'select(User).where(User.id == user_id).with_for_update()'
    assert free_lock in source
    assert source.index(free_lock) < source.index('select(PremiumPlan).where(PremiumPlan.code == FREE_PLAN_CODE)')


def test_schema_is_alembic_authoritative_in_runtime_and_scale_ci() -> None:
    main = read("main_v2.py")
    auth_workflow = read(".github/workflows/auth-quota-db-scale.yml")
    replica_workflow = read(".github/workflows/multireplica-db-scale.yml")
    seed_auth = read("tools/seed_quota_scale_db.py")
    seed_scale = read("tools/seed_scale_db.py")

    assert 'ALLOW_RUNTIME_SCHEMA_BOOTSTRAP", "false"' in main
    assert "alembic upgrade head" in auth_workflow
    assert "alembic upgrade head" in replica_workflow
    assert "Base.metadata.create_all" not in seed_auth
    assert "Base.metadata.create_all" not in seed_scale
    assert "TRUNCATE TABLE users, premium_plans, feedback_submissions" in seed_scale


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


def test_audit_runs_session_concurrency_regression() -> None:
    workflow = read(".github/workflows/hybrid-reconciled-audit.yml")
    assert "test_hybrid_session_concurrency.py" in workflow


def test_session_creation_preserves_uuid_on_integrity_conflict() -> None:
    source = read("main_v2.py")
    assert "except IntegrityError:" in source
    assert "Another concurrent request may have inserted the same" in source
    assert "return session_uuid, int(existing.id)" in source
    assert '.where(UserSession.session_uuid == requested_uuid)' in source
    assert '.with_for_update()' in source


def test_audit_runs_p0_quota_regression() -> None:
    workflow = read(".github/workflows/hybrid-reconciled-audit.yml")
    assert "test_p0_quota_consumption.py" in workflow
    assert "test_billing_idempotency.py" in workflow
