"""Persist final journey result summary on operational sessions.

Revision ID: 0007_result_summary
Revises: 0006_user_session_owner
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_result_summary"
down_revision = "0006_user_session_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_sessions",
        sa.Column("result_summary", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_sessions", "result_summary")
