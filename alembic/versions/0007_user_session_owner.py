"""Link operational journey sessions to authenticated users.

Revision ID: 0007_user_session_owner
Revises: 0006_user_session_owner
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_user_session_owner"
down_revision = "0006_user_session_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("user_id", sa.BigInteger(), nullable=True))
    op.create_index("idx_session_user_created", "user_sessions", ["user_id", "created_at"])
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
    op.drop_index("idx_session_user_created", table_name="user_sessions")
    op.drop_column("user_sessions", "user_id")
