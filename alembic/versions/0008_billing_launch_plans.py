"""Seed the canonical free and commercial credit plans.

The free plan is required for every authenticated user's initial test. The
commercial plan remains inactive until payment configuration is deliberately
turned on; this migration does not activate any provider.
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_billing_launch_plans"
down_revision = "0007_result_summary"
branch_labels = None
depends_on = None


FREE_PLAN = {
    "code": "free_1_test",
    "name_fa": "تست رایگان",
    "plan_type": "credits",
    "duration_days": None,
    "credits_granted": 1,
    "price_minor": 0,
    "currency": "IRR",
    "is_active": True,
}

PACK_PLAN = {
    "code": "pack_3_tests",
    "name_fa": "بسته ۳ تست",
    "plan_type": "credits",
    "duration_days": None,
    "credits_granted": 3,
    "price_minor": 2_490_000,
    "currency": "IRR",
    "is_active": False,
}


def _upsert_plan(plan: dict) -> None:
    connection = op.get_bind()
    stmt = sa.text(
        """
        INSERT INTO premium_plans
            (code, name_fa, plan_type, duration_days, credits_granted,
             price_minor, currency, is_active, features)
        VALUES
            (:code, :name_fa, :plan_type, :duration_days, :credits_granted,
             :price_minor, :currency, :is_active, :features)
        ON CONFLICT (code) DO UPDATE SET
            name_fa = EXCLUDED.name_fa,
            plan_type = EXCLUDED.plan_type,
            duration_days = EXCLUDED.duration_days,
            credits_granted = EXCLUDED.credits_granted,
            price_minor = EXCLUDED.price_minor,
            currency = EXCLUDED.currency,
            is_active = EXCLUDED.is_active
        """
    )
    connection.execute(stmt, {**plan, "features": "{}"})


def upgrade() -> None:
    _upsert_plan(FREE_PLAN)
    _upsert_plan(PACK_PLAN)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM premium_plans
            WHERE code IN ('free_1_test', 'pack_3_tests')
              AND NOT EXISTS (
                  SELECT 1 FROM entitlements e WHERE e.plan_id = premium_plans.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM orders o WHERE o.plan_id = premium_plans.id
              )
            """
        )
    )
