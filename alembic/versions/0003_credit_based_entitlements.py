"""Convert premium model to credit-based test packs.

Revision ID: 0003_credit_based_entitlements
Revises: 0002_auth_billing
Create Date: 2026-08-29

Product is not a time-based subscription. Free access is one test; paid
``pack_3_tests`` grants exactly three additional credits after verified payment.
Expiration is optional and therefore nullable.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_credit_based_entitlements"
down_revision = "0002_auth_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("premium_plans", sa.Column("plan_type", sa.String(20), nullable=False, server_default="credits"))
    op.alter_column("premium_plans", "duration_days", existing_type=sa.Integer(), nullable=True)
    op.add_column("premium_plans", sa.Column("credits_granted", sa.Integer(), nullable=False, server_default="0"))

    op.add_column("entitlements", sa.Column("credits_granted", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("entitlements", sa.Column("credits_remaining", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("entitlements", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=True)
    op.create_index("idx_entitlement_user_credits", "entitlements", ["user_id", "credits_remaining"])

    # Stored money uses Rial (IRR). 249,000 Toman = 2,490,000 Rial.
    free_plan_sql = sa.text(
        "INSERT INTO premium_plans "
        "(code, name_fa, plan_type, duration_days, credits_granted, price_minor, currency, is_active, features) "
        "VALUES (:code, :name_fa, 'credits', NULL, 1, 0, 'IRR', TRUE, CAST(:features AS jsonb)) "
        "ON CONFLICT (code) DO NOTHING"
    ).bindparams(
        code="free_1_test",
        name_fa="رایگان — ۱ تست",
        features='{"tests": 1, "non_expiring": true}',
    )
    op.execute(free_plan_sql)

    pack_sql = sa.text(
        "INSERT INTO premium_plans "
        "(code, name_fa, plan_type, duration_days, credits_granted, price_minor, currency, is_active, features) "
        "VALUES (:code, :name_fa, 'credits', NULL, 3, 2490000, 'IRR', TRUE, CAST(:features AS jsonb)) "
        "ON CONFLICT (code) DO NOTHING"
    ).bindparams(
        code="pack_3_tests",
        name_fa="بسته ۳ تست",
        features='{"tests": 3, "non_expiring": true}',
    )
    op.execute(pack_sql)


def downgrade() -> None:
    op.drop_index("idx_entitlement_user_credits", table_name="entitlements")
    op.alter_column("entitlements", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.drop_column("entitlements", "credits_remaining")
    op.drop_column("entitlements", "credits_granted")
    op.drop_column("premium_plans", "credits_granted")
    op.alter_column("premium_plans", "duration_days", existing_type=sa.Integer(), nullable=False)
    op.drop_column("premium_plans", "plan_type")
