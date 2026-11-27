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
    # Reuse the existing admin audit ledger as the code registry. The partial
    # unique index keeps codes unique without introducing a new Hybrid table.
    op.create_index(
        "uq_admin_audit_referral_code",
        "admin_audit_logs",
        ["target_id"],
        unique=True,
        postgresql_where=sa.text("target_type = 'referral_code' AND action = 'create_referral_code'"),
        sqlite_where=sa.text("target_type = 'referral_code' AND action = 'create_referral_code'"),
    )

    op.add_column("users", sa.Column("referral_code", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("referral_locked_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("orders", sa.Column("referral_code_snapshot", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("referral_label_snapshot", sa.String(length=200), nullable=True))
    op.add_column("orders", sa.Column("referral_snapshot_at", sa.DateTime(timezone=True), nullable=True))


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
    op.drop_column("orders", "referral_snapshot_at")
    op.drop_column("orders", "referral_label_snapshot")
    op.drop_column("orders", "referral_code_snapshot")
    op.drop_column("users", "referral_locked_at")
    op.drop_column("users", "referral_code")
    op.drop_index("uq_admin_audit_referral_code", table_name="admin_audit_logs")
