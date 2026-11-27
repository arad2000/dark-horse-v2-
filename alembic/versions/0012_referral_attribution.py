"""Add referral-code attribution and immutable paid-order snapshots.

Revision ID: 0012_referral_attribution
Revises: 0011_otp_request_ip

Attribution-only schema. Does not alter payment amounts, product plans,
commission economics, wallet, payout, settlement, or scoring data.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_referral_attribution"
down_revision = "0011_otp_request_ip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_referral_code"),
    )
    op.create_index("idx_referral_code_active", "referral_codes", ["is_active"])

    op.add_column("users", sa.Column("referral_code", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("referral_locked_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("orders", sa.Column("referral_code_id", sa.BigInteger(), nullable=True))
    op.add_column("orders", sa.Column("referral_code_snapshot", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("referral_label_snapshot", sa.String(length=200), nullable=True))
    op.add_column("orders", sa.Column("referral_snapshot_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_orders_referral_code_id",
        "orders",
        "referral_codes",
        ["referral_code_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Existing paid accounts are already past the edit window. Preserve that
    # invariant during rollout even though historical orders get no attribution.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET referral_locked_at = (
                SELECT MIN(o.paid_at)
                FROM orders AS o
                WHERE o.user_id = users.id
                  AND o.status = 'paid'
                  AND o.paid_at IS NOT NULL
            )
            WHERE referral_locked_at IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM orders AS o
                  WHERE o.user_id = users.id
                    AND o.status = 'paid'
                    AND o.paid_at IS NOT NULL
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_orders_referral_code_id", "orders", type_="foreignkey")
    op.drop_column("orders", "referral_snapshot_at")
    op.drop_column("orders", "referral_label_snapshot")
    op.drop_column("orders", "referral_code_snapshot")
    op.drop_column("orders", "referral_code_id")
    op.drop_column("users", "referral_locked_at")
    op.drop_column("users", "referral_code")
    op.drop_index("idx_referral_code_active", table_name="referral_codes")
    op.drop_table("referral_codes")
