import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect, text


EXPECTED_TABLES = {
    "micro_motives",
    "value_poles",
    "trait_options",
    "majors",
    "school_branches",
    "major_micro_motives",
    "branch_micro_motives",
    "user_sessions",
    "discovery_results",
    "branch_recommendations",
    "user_feedback",
    "audit_logs",
    "users",
    "auth_sessions",
    "premium_plans",
    "orders",
    "payments",
    "entitlements",
    "payment_events",
    "admin_audit_logs",
    "feedback_submissions",
    "registration_challenges",
    "saved_results",
}

EXPECTED_INDEXES = {
    "uq_payment_provider_transaction",
    "idx_saved_results_user_created",
    "idx_saved_results_session",
    "idx_registration_challenge_phone",
    "idx_registration_challenge_expiry",
}


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value.startswith("postgresql"):
        pytest.skip("PostgreSQL DATABASE_URL is not configured")
    return value


def _run_alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        check=True,
        env=os.environ.copy(),
    )


def _scalar(conn, sql: str, params: dict | None = None):
    return conn.execute(text(sql), params or {}).scalar()


def test_postgresql_full_migration_round_trip():
    url = _database_url()
    engine = create_engine(url, future=True)

    _run_alembic("upgrade", "head")

    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert EXPECTED_TABLES.issubset(tables)

        with engine.connect() as conn:
            alembic_revision = _scalar(conn, "SELECT version_num FROM alembic_version")
        assert alembic_revision == "0007_auth_saved_results"

        # PostgreSQL identity/autoincrement behavior for all newly-added BIGINT PKs.
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (public_id, name, phone) "
                    "VALUES ('smoke-user-1', 'Smoke', '+491700000001')"
                )
            )
            user_id = _scalar(conn, "SELECT id FROM users WHERE public_id='smoke-user-1'")
            assert isinstance(user_id, int)
            assert user_id > 0

            conn.execute(
                text(
                    "INSERT INTO registration_challenges "
                    "(challenge_id, name, phone, password_hash, code_hash, expires_at) "
                    "VALUES ('smoke-challenge-1', 'Smoke', '+491700000002', 'p', 'c', NOW())"
                )
            )
            challenge_id = _scalar(
                conn,
                "SELECT id FROM registration_challenges WHERE challenge_id='smoke-challenge-1'",
            )
            assert isinstance(challenge_id, int)
            assert challenge_id > 0

            conn.execute(
                text(
                    "INSERT INTO saved_results (user_id, result_summary) "
                    "VALUES (:user_id, CAST(:summary AS jsonb))"
                ),
                {"user_id": user_id, "summary": '{"ok":true}'},
            )
            saved_id = _scalar(
                conn,
                "SELECT id FROM saved_results WHERE user_id=:user_id",
                {"user_id": user_id},
            )
            assert isinstance(saved_id, int)
            assert saved_id > 0

            # Nullable transaction identifiers may repeat; real transaction IDs may not.
            conn.execute(
                text(
                    "INSERT INTO premium_plans "
                    "(code, name_fa, plan_type, duration_days, credits_granted, price_minor, currency, features) "
                    "VALUES ('smoke-plan', 'Smoke', 'credits', NULL, 1, 0, 'IRR', CAST(:features AS jsonb)) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                {"features": '{"tests":1}'},
            )
            plan_id = _scalar(conn, "SELECT id FROM premium_plans WHERE code='smoke-plan'")
            conn.execute(
                text(
                    "INSERT INTO orders (public_id, user_id, plan_id, amount_minor, currency) "
                    "VALUES ('smoke-order-1', :user_id, :plan_id, 0, 'IRR')"
                ),
                {"user_id": user_id, "plan_id": plan_id},
            )
            order_id = _scalar(conn, "SELECT id FROM orders WHERE public_id='smoke-order-1'")
            conn.execute(
                text(
                    "INSERT INTO payments (order_id, provider, provider_transaction_id, amount_minor, currency) "
                    "VALUES (:order_id, 'mock', NULL, 0, 'IRR')"
                ),
                {"order_id": order_id},
            )
            conn.execute(
                text(
                    "INSERT INTO payments (order_id, provider, provider_transaction_id, amount_minor, currency) "
                    "VALUES (:order_id, 'mock', NULL, 0, 'IRR')"
                ),
                {"order_id": order_id},
            )
            conn.execute(
                text(
                    "INSERT INTO payments (order_id, provider, provider_transaction_id, amount_minor, currency) "
                    "VALUES (:order_id, 'mock', 'txn-1', 0, 'IRR')"
                ),
                {"order_id": order_id},
            )
            with pytest.raises(Exception):
                with conn.begin_nested():
                    conn.execute(
                        text(
                            "INSERT INTO payments (order_id, provider, provider_transaction_id, amount_minor, currency) "
                            "VALUES (:order_id, 'mock', 'txn-1', 0, 'IRR')"
                        ),
                        {"order_id": order_id},
                    )

        index_names = {
            item["name"]
            for table in EXPECTED_TABLES
            for item in inspector.get_indexes(table)
            if item.get("name")
        }
        assert EXPECTED_INDEXES.issubset(index_names)

        # Ensure the partial unique index really excludes NULL transaction IDs.
        with engine.connect() as conn:
            predicate = conn.execute(
                text(
                    "SELECT pg_get_expr(i.indpred, i.indrelid) "
                    "FROM pg_index i "
                    "JOIN pg_class c ON c.oid=i.indexrelid "
                    "WHERE c.relname='uq_payment_provider_transaction'"
                )
            ).scalar()
            assert predicate == "(provider_transaction_id IS NOT NULL)"
    finally:
        _run_alembic("downgrade", "base")
        _run_alembic("upgrade", "head")
        _run_alembic("downgrade", "base")
        engine.dispose()
