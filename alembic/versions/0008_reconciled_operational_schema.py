"""Reconcile operational schema with authenticated runtime models.

Revision ID: 0008_reconciled_operational_schema
Revises: 0007_auth_challenges_saved_results

This single migration replaces two conflicting 0008 revisions. It widens
operational integer identifiers to BIGINT, aligns dependent session foreign
keys, and adds the nullable authenticated owner on user_sessions.
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_reconciled_operational_schema"
down_revision = "0007_auth_challenges_saved_results"
branch_labels = None
depends_on = None


def _widen_pk(table: str, column: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.alter_column(column, existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)


def upgrade() -> None:
    _widen_pk("user_sessions", "id")
    _widen_pk("discovery_results", "id")
    _widen_pk("branch_recommendations", "id")
    _widen_pk("user_feedback", "id")
    _widen_pk("audit_logs", "id")
    _widen_pk("audit_logs", "record_id")

    with op.batch_alter_table("discovery_results") as batch:
        batch.drop_constraint("discovery_results_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
        batch.create_foreign_key(
            "discovery_results_session_id_fkey", "user_sessions", ["session_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("branch_recommendations") as batch:
        batch.drop_constraint("branch_recommendations_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
        batch.create_foreign_key(
            "branch_recommendations_session_id_fkey", "user_sessions", ["session_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("user_feedback") as batch:
        batch.drop_constraint("user_feedback_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
        batch.create_foreign_key(
            "user_feedback_session_id_fkey", "user_sessions", ["session_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("user_sessions") as batch:
        batch.add_column(sa.Column("user_id", sa.BigInteger(), nullable=True))
        batch.create_index("idx_session_user", ["user_id"])
        batch.create_foreign_key(
            "user_sessions_user_id_fkey", "users", ["user_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("user_sessions") as batch:
        batch.drop_constraint("user_sessions_user_id_fkey", type_="foreignkey")
        batch.drop_index("idx_session_user")
        batch.drop_column("user_id")

    with op.batch_alter_table("user_feedback") as batch:
        batch.drop_constraint("user_feedback_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
        batch.create_foreign_key(
            "user_feedback_session_id_fkey", "user_sessions", ["session_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("branch_recommendations") as batch:
        batch.drop_constraint("branch_recommendations_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
        batch.create_foreign_key(
            "branch_recommendations_session_id_fkey", "user_sessions", ["session_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("discovery_results") as batch:
        batch.drop_constraint("discovery_results_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
        batch.create_foreign_key(
            "discovery_results_session_id_fkey", "user_sessions", ["session_id"], ["id"], ondelete="CASCADE"
        )

    _restore_order = [
        ("audit_logs", "record_id"),
        ("audit_logs", "id"),
        ("user_feedback", "id"),
        ("branch_recommendations", "id"),
        ("discovery_results", "id"),
        ("user_sessions", "id"),
    ]
    for table, column in _restore_order:
        with op.batch_alter_table(table) as batch:
            batch.alter_column(column, existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
