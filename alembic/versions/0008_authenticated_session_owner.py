"""Bind operational sessions to authenticated users and align PostgreSQL key widths.

Revision ID: 0008_authenticated_session_owner
Revises: 0007_auth_challenges_saved_results

The reconciled runtime stores the authenticated owner on user_sessions. The
initial hybrid schema used INTEGER operational keys; the current ORM uses
BIGINT consistently for runtime-generated operational identifiers. This
migration widens the affected operational keys and adds the nullable owner FK.
Existing anonymous sessions remain valid because user_id is nullable.
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_authenticated_session_owner"
down_revision = "0007_auth_challenges_saved_results"
branch_labels = None
depends_on = None


def _alter_pk_and_fk_types(table: str, column: str, fk_table: str | None = None) -> None:
    if fk_table:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"{table}_{column}_fkey", type_="foreignkey")
            batch.alter_column(column, existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
    else:
        with op.batch_alter_table(table) as batch:
            batch.alter_column(column, existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)


def upgrade() -> None:
    # Widen the operational primary keys first, then their dependent FKs.
    _alter_pk_and_fk_types("user_sessions", "id")
    _alter_pk_and_fk_types("discovery_results", "id")
    _alter_pk_and_fk_types("branch_recommendations", "id")
    _alter_pk_and_fk_types("user_feedback", "id")
    _alter_pk_and_fk_types("audit_logs", "id")
    _alter_pk_and_fk_types("audit_logs", "record_id")

    with op.batch_alter_table("discovery_results") as batch:
        batch.drop_constraint("discovery_results_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
        batch.create_foreign_key(
            "discovery_results_session_id_fkey",
            "user_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("branch_recommendations") as batch:
        batch.drop_constraint("branch_recommendations_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
        batch.create_foreign_key(
            "branch_recommendations_session_id_fkey",
            "user_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("user_feedback") as batch:
        batch.drop_constraint("user_feedback_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
        batch.create_foreign_key(
            "user_feedback_session_id_fkey",
            "user_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("user_sessions") as batch:
        batch.add_column(sa.Column("user_id", sa.BigInteger(), nullable=True))
        batch.create_index("idx_session_user", ["user_id"])
        batch.create_foreign_key(
            "user_sessions_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
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
            "user_feedback_session_id_fkey",
            "user_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("branch_recommendations") as batch:
        batch.drop_constraint("branch_recommendations_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
        batch.create_foreign_key(
            "branch_recommendations_session_id_fkey",
            "user_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("discovery_results") as batch:
        batch.drop_constraint("discovery_results_session_id_fkey", type_="foreignkey")
        batch.alter_column("session_id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
        batch.create_foreign_key(
            "discovery_results_session_id_fkey",
            "user_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

    _alter_pk_and_fk_types("audit_logs", "record_id")
    with op.batch_alter_table("audit_logs") as batch:
        batch.alter_column("record_id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
        batch.alter_column("id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
    with op.batch_alter_table("user_feedback") as batch:
        batch.alter_column("id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
    with op.batch_alter_table("branch_recommendations") as batch:
        batch.alter_column("id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
    with op.batch_alter_table("discovery_results") as batch:
        batch.alter_column("id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
    with op.batch_alter_table("user_sessions") as batch:
        batch.alter_column("id", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
