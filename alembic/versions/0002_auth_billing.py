"""Add staged authentication, premium and billing tables.

Revision ID: 0002_auth_billing
Revises: 0001_initial_hybrid_schema
Create Date: 2026-08-28

Operational-only. This migration does not alter the scoring engine, reference
JSON, or PostgreSQL runtime cutover state.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_auth_billing"
down_revision = "0001_initial_hybrid_schema"
branch_labels = None
depends_on = None

JSON_TYPE = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
BIGINT_TYPE = sa.BigInteger()


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("public_id", name="uq_users_public_id"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
    )
    op.create_index("idx_users_status", "users", ["status"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("user_id", BIGINT_TYPE, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash", name="uq_auth_session_token_hash"),
    )
    op.create_index("idx_auth_session_expiry", "auth_sessions", ["expires_at"])

    op.create_table(
        "premium_plans",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_fa", sa.String(200), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("price_minor", BIGINT_TYPE, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="IRR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("features", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_premium_plan_code"),
    )

    op.create_table(
        "orders",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("user_id", BIGINT_TYPE, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("plan_id", BIGINT_TYPE, sa.ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_minor", BIGINT_TYPE, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("public_id", name="uq_order_public_id"),
    )
    op.create_index("idx_orders_status", "orders", ["status"])

    op.create_table(
        "payments",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("order_id", BIGINT_TYPE, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_request_id", sa.String(128), nullable=True),
        sa.Column("provider_authority", sa.String(128), nullable=True),
        sa.Column("provider_transaction_id", sa.String(128), nullable=True),
        sa.Column("amount_minor", BIGINT_TYPE, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="initiated"),
        sa.Column("raw_callback", JSON_TYPE, nullable=True),
        sa.Column("verification_response", JSON_TYPE, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_payments_provider_authority", "payments", ["provider", "provider_authority"])
    op.create_index("idx_payments_status", "payments", ["status"])

    op.create_table(
        "entitlements",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("user_id", BIGINT_TYPE, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", BIGINT_TYPE, sa.ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("order_id", BIGINT_TYPE, sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_entitlement_user_status", "entitlements", ["user_id", "status"])

    op.create_table(
        "payment_events",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("payment_id", BIGINT_TYPE, sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_key", sa.String(200), nullable=False),
        sa.Column("payload", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("event_key", name="uq_payment_event_key"),
    )
    op.create_index("idx_payment_event_payment", "payment_events", ["payment_id"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", BIGINT_TYPE, primary_key=True),
        sa.Column("admin_user_id", BIGINT_TYPE, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=False),
        sa.Column("metadata", JSON_TYPE, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_admin_audit_created", "admin_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_admin_audit_created", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_index("idx_payment_event_payment", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_index("idx_entitlement_user_status", table_name="entitlements")
    op.drop_table("entitlements")
    op.drop_index("idx_payments_status", table_name="payments")
    op.drop_index("idx_payments_provider_authority", table_name="payments")
    op.drop_table("payments")
    op.drop_index("idx_orders_status", table_name="orders")
    op.drop_table("orders")
    op.drop_table("premium_plans")
    op.drop_index("idx_auth_session_expiry", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("idx_users_status", table_name="users")
    op.drop_table("users")
