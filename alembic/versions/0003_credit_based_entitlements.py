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
from sqlalchemy.dialects import postgresql

revision = "0003_credit_based_entitlements"
down_revision = "0002_auth_billing"
branch_labels = None
depends_on = None
JSON_TYPE = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.add_column("premium_plans", sa.Column("plan_type", sa.String(20), nullable=False, server_default="credits"))
    op.alter_column("premium_plans", "duration_days", existing_type=sa.Integer(), nullable=True)
    op.add_column("premium_plans", sa.Column("credits_granted", sa.Integer(), nullable=False, server_default="0"))

    op.add_column("entitlements", sa.Column("credits_granted", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("entitlements", sa.Column("credits_remaining", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("entitlements", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=True)
    op.create_index("idx_entitlement_user_credits", "entitlements", ["user_id", "credits_remaining"])

    # Canonical free and paid credit products. Amounts use Rial as the stored
    # smallest unit: 249,000 Toman = 2,490,000 Rial.
    premium_plans = sa.table(
        "premium_plans",
        sa.column("id", sa.BigInteger()),
        sa.column("code", sa.String()),
        sa.column("name_fa", sa.String()),
        sa.column("plan_type", sa.String()),
        sa.column("duration_days", sa.Integer()),
        sa.column("credits_granted", sa.Integer()),
        sa.column("price_minor", sa.BigInteger()),
        sa.column("currency", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("features", JSON_TYPE),
    )
    op.execute(
        premium_plans.insert().values(
            id=1,
            code="free_1_test",
            name_fa="رایگان — ۱ تست",
            plan_type="credits",
            duration_days=None,
            credits_granted=1,
            price_minor=0,
            currency="IRR",
            is_active=True,
            features={"tests": 1, "non_expiring": True},
        ).on_conflict_do_nothing(index_elements=["code"])
    ) if hasattr(premium_plans.insert(), "on_conflict_do_nothing") else None

    op.execute(
        sa.text(
            "INSERT INTO premium_plans "
            "(code, name_fa, plan_type, duration_days, credits_granted, price_minor, currency, is_active, features) "
            "VALUES (:code, :name_fa, :plan_type, NULL, 3, 2490000, 'IRR', TRUE, :features) "
            "ON CONFLICT (code) DO NOTHING"
        ),
        {
            "code": "pack_3_tests",
            "name_fa": "بسته ۳ تست",
            "plan_type": "credits",
            "features": '{"tests": 3, "non_expiring": true}',
        },
    )


def downgrade() -> None:
    op.drop_index("idx_entitlement_user_credits", table_name="entitlements")
    op.alter_column("entitlements", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.drop_column("entitlements", "credits_remaining")
    op.drop_column("entitlements", "credits_granted")
    op.drop_column("premium_plans", "credits_granted")
    op.alter_column("premium_plans", "duration_days", existing_type=sa.Integer(), nullable=False)
    op.drop_column("premium_plans", "plan_type")
