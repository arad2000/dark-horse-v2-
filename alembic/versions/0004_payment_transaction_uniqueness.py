"""Guard payment provider transaction identity against double settlement.

Revision ID: 0004_payment_transaction_uniqueness
Revises: 0003_credit_based_entitlements
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_payment_transaction_uniqueness"
down_revision = "0003_credit_based_entitlements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_payment_provider_transaction",
        "payments",
        ["provider", "provider_transaction_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payment_provider_transaction", "payments", type_="unique")
