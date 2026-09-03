"""Add standalone web feedback submissions.

Revision ID: 0006_feedback_submissions
Revises: 0005_payment_transaction_partial_unique
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_feedback_submissions"
down_revision = "0005_payment_transaction_partial_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_uuid", sa.String(length=36), nullable=True),
        sa.Column("exam_code", sa.String(length=64), nullable=True),
        sa.Column("exam_date", sa.String(length=40), nullable=True),
        sa.Column("suggested_major", sa.String(length=200), nullable=True),
        sa.Column("suggested_score", sa.Integer(), nullable=True),
        sa.Column("major_fit", sa.Integer(), nullable=False),
        sa.Column("motive_accuracy", sa.Integer(), nullable=False),
        sa.Column("strategy_fit", sa.Integer(), nullable=False),
        sa.Column("value_fit", sa.Integer(), nullable=False),
        sa.Column("nps", sa.Integer(), nullable=False),
        sa.Column("desired_major", sa.String(length=200), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="web"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_feedback_submissions_id", "feedback_submissions", ["id"], unique=False)
    op.create_index("ix_feedback_submissions_session_uuid", "feedback_submissions", ["session_uuid"], unique=False)
    op.create_index("idx_feedback_submissions_created", "feedback_submissions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_feedback_submissions_created", table_name="feedback_submissions")
    op.drop_index("ix_feedback_submissions_session_uuid", table_name="feedback_submissions")
    op.drop_index("ix_feedback_submissions_id", table_name="feedback_submissions")
    op.drop_table("feedback_submissions")
