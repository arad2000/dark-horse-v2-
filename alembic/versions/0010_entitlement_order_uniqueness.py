"""Ensure one paid entitlement can exist per order."""
from alembic import op
import sqlalchemy as sa

revision = "0010_entitlement_order_unique"
down_revision = "0009_journey_credit_consumptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
