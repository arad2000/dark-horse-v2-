"""Add an independent idempotency ledger for journey credit charges."""
from alembic import op
import sqlalchemy as sa

revision = "0009_journey_credit_consumptions"
down_revision = "0008_reconciled_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journey_credit_consumptions",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_uuid", sa.String(length=64), nullable=False),
        sa.Column(
            "entitlement_id",
            sa.BigInteger(),
            sa.ForeignKey("entitlements.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_uuid", name="uq_journey_credit_consumption_session"),
    )
    op.create_index(
        "idx_journey_credit_consumption_user",
        "journey_credit_consumptions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_journey_credit_consumption_user",
        table_name="journey_credit_consumptions",
    )
    op.drop_table("journey_credit_consumptions")