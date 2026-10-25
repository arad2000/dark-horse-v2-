"""Link operational journey sessions to authenticated users.

Revision ID: 0006_user_session_owner
Revises: 0005_phone_verification
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_user_session_owner"
down_revision = "0005_phone_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_sessions",
        sa.Column("user_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_sessions_user_id_users",
        "user_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_user_sessions_user_id",
        "user_sessions",
        ["user_id"],
    )
    op.create_index(
        "idx_session_user_created",
        "user_sessions",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_session_user_created", table_name="user_sessions")
    op.drop_index("idx_user_sessions_user_id", table_name="user_sessions")
    op.drop_constraint("fk_user_sessions_user_id_users", "user_sessions", type_="foreignkey")
    op.drop_column("user_sessions", "user_id")
