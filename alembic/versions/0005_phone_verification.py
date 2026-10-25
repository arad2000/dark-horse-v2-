"""Add phone verification challenges for OTP registration.

Revision ID: 0005_phone_verification
Revises: 0004_txn_unique
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_phone_verification"
down_revision = "0004_txn_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phone_verifications",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("challenge_id", sa.String(length=128), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="register"),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id", name="uq_phone_verification_challenge"),
    )
    op.create_index(
        "idx_phone_verification_phone",
        "phone_verifications",
        ["phone", "purpose", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_phone_verification_phone", table_name="phone_verifications")
    op.drop_table("phone_verifications")
