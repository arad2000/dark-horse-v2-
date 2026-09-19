"""Replace nullable payment transaction uniqueness with a PostgreSQL partial unique index.

Revision ID: 0005_payment_txn_partial_unique
Revises: 0004_txn_unique
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_payment_txn_partial_unique"
down_revision = "0004_txn_unique"
branch_labels = None
depends_on = None


INDEX_NAME = "uq_payment_provider_transaction"


def upgrade() -> None:
    # PostgreSQL permits multiple NULL values in a UNIQUE constraint. Only a
    # real provider transaction identity should participate in uniqueness.
    op.drop_constraint(INDEX_NAME, "payments", type_="unique")
    op.create_index(
        INDEX_NAME,
        "payments",
        ["provider", "provider_transaction_id"],
        unique=True,
        postgresql_where=sa.text("provider_transaction_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="payments")
    op.create_unique_constraint(
        INDEX_NAME,
        "payments",
        ["provider", "provider_transaction_id"],
    )
