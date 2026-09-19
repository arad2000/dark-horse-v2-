"""Ensure one paid entitlement can exist per order."""
from alembic import op
import sqlalchemy as sa

revision = "0010_entitlement_order_unique"
down_revision = "0009_journey_credit_consumptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT order_id, COUNT(*) AS entitlement_count
            FROM entitlements
            WHERE order_id IS NOT NULL
            GROUP BY order_id
            HAVING COUNT(*) > 1
            ORDER BY entitlement_count DESC, order_id
            LIMIT 10
            """
        )
    ).fetchall()
    if duplicates:
        examples = ", ".join(
            f"order_id={row.order_id} count={row.entitlement_count}"
            for row in duplicates
        )
        raise RuntimeError(
            "Cannot enforce uq_entitlement_order: duplicate paid entitlements exist; "
            f"reconcile these orders first: {examples}"
        )

    op.create_unique_constraint(
        "uq_entitlement_order",
        "entitlements",
        ["order_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_entitlement_order",
        "entitlements",
        type_="unique",
    )
