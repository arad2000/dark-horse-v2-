"""Align user_sessions with authenticated-session ownership used by runtime.

Revision ID: 0008_reconcile_session_user_fk
Revises: 0007_auth_challenges_saved_results
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_reconcile_session_user_fk"
down_revision = "0007_auth_challenges_saved_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_sessions",
        sa.Column("user_id", sa.BigInteger(), nullable=True),
    )
    op.create_index("idx_session_user", "user_sessions", ["user_id"])
    op.create_foreign_key(
        "fk_user_sessions_user_id",
        "user_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_user_sessions_user_id", "user_sessions", type_="foreignkey")
    op.drop_index("idx_session_user", table_name="user_sessions")
    op.drop_column("user_sessions", "user_id")
