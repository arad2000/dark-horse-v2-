"""Add durable registration OTP challenges and authenticated saved results.

Revision ID: 0007_auth_challenges_saved_results
Revises: 0006_feedback_submissions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_auth_challenges_saved_results"
down_revision = "0006_feedback_submissions"
branch_labels = None
depends_on = None

JSON_TYPE = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "registration_challenges",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("challenge_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("challenge_id", name="uq_registration_challenge_id"),
    )
    op.create_index("idx_registration_challenge_phone", "registration_challenges", ["phone"])
    op.create_index("idx_registration_challenge_expiry", "registration_challenges", ["expires_at"])

    op.create_table(
        "saved_results",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_uuid", sa.String(length=36), nullable=True),
        sa.Column("result_summary", JSON_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_saved_results_user_created", "saved_results", ["user_id", "created_at"])
    op.create_index("idx_saved_results_session", "saved_results", ["session_uuid"])


def downgrade() -> None:
    op.drop_index("idx_saved_results_session", table_name="saved_results")
    op.drop_index("idx_saved_results_user_created", table_name="saved_results")
    op.drop_table("saved_results")
    op.drop_index("idx_registration_challenge_expiry", table_name="registration_challenges")
    op.drop_index("idx_registration_challenge_phone", table_name="registration_challenges")
    op.drop_table("registration_challenges")
