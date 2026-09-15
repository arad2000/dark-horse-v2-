"""Seed the canonical free and commercial credit plans.

The free plan is required for every authenticated user's initial test. The
commercial plan remains inactive until payment configuration is deliberately
turned on; this migration does not activate any provider.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

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
    "features": {},
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
    "features": {},
}


def _upsert_plan(plan: dict) -> None:
    connection = op.get_bind()
    table = sa.table(
        "premium_plans",
        sa.column("code", sa.String(64)),
        sa.column("name_fa", sa.String(200)),
        sa.column("plan_type", sa.String(20)),
        sa.column("duration_days", sa.Integer()),
        sa.column("credits_granted", sa.Integer()),
        sa.column("price_minor", sa.BigInteger()),
        sa.column("currency", sa.String(8)),
        sa.column("is_active", sa.Boolean()),
        sa.column("features", sa.JSON()),
    )
    stmt = pg_insert(table).values(**plan)
    stmt = stmt.on_conflict_do_update(
        index_elements=[table.c.code],
        set_={
            "name_fa": stmt.excluded.name_fa,
            "plan_type": stmt.excluded.plan_type,
            "duration_days": stmt.excluded.duration_days,
            "credits_granted": stmt.excluded.credits_granted,
            "price_minor": stmt.excluded.price_minor,
            "currency": stmt.excluded.currency,
            "is_active": stmt.excluded.is_active,
        },
    )
    connection.execute(stmt)


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
