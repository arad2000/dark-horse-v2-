"""Create the initial Dark Horse Hybrid operational schema.

Revision ID: 0001_initial_hybrid_schema
Revises:
Create Date: 2026-08-27

This migration creates only the PostgreSQL schema. It does not import JSON
reference data, alter the scoring engine, or enable PostgreSQL runtime use.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_hybrid_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "micro_motives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("description_fa", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("intensity_level", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_motive_code"),
    )
    op.create_index("idx_motive_category", "micro_motives", ["category"])

    op.create_table(
        "value_poles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pole_code", sa.String(length=16), nullable=False),
        sa.Column("question_num", sa.Integer(), nullable=False),
        sa.Column("option_letter", sa.String(length=1), nullable=False),
        sa.Column("description_fa", sa.String(length=300), nullable=False),
        sa.Column("opposite_pole_id", sa.Integer(), sa.ForeignKey("value_poles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("pole_code", name="uq_pole_code"),
    )
    op.create_index("idx_value_question", "value_poles", ["question_num"])

    op.create_table(
        "trait_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_code", sa.String(length=10), nullable=False),
        sa.Column("option_index", sa.Integer(), nullable=False),
        sa.Column("traits", sa.JSON(), nullable=True),
        sa.Column("description_fa", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("question_code", "option_index", name="uq_question_option"),
    )
    op.create_index("idx_question_code", "trait_options", ["question_code"])

    op.create_table(
        "majors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("group", sa.String(length=100), nullable=False),
        sa.Column("cluster", sa.String(length=20), nullable=True),
        sa.Column("subgroup", sa.String(length=80), nullable=True),
        sa.Column("exam_group", sa.String(length=80), nullable=True),
        sa.Column("high_school_branch", sa.String(length=100), nullable=True),
        sa.Column("strategy_weights", sa.JSON(), nullable=False),
        sa.Column("value_weights", sa.JSON(), nullable=False),
        sa.Column("archetype", sa.String(length=200), nullable=True),
        sa.Column("fulfillment_source", sa.Text(), nullable=True),
        sa.Column("prestige_level", sa.Integer(), nullable=True),
        sa.Column("handcrafted", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("motive_driven", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weights_version", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("name", name="uq_major_name"),
    )
    op.create_index("idx_major_group", "majors", ["group"])
    op.create_index("idx_major_cluster", "majors", ["cluster"])

    op.create_table(
        "school_branches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("group", sa.String(length=50), nullable=False),
        sa.Column("m_score_denom_limit", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("strategy_weights", sa.JSON(), nullable=False),
        sa.Column("value_weights", sa.JSON(), nullable=False),
        sa.Column("weights_version", sa.String(length=100), nullable=True),
        sa.Column("source_majors_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("name", name="uq_branch_name"),
    )

    op.create_table(
        "major_micro_motives",
        sa.Column("major_id", sa.Integer(), sa.ForeignKey("majors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("motive_id", sa.Integer(), sa.ForeignKey("micro_motives.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "branch_micro_motives",
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("school_branches.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("motive_id", sa.Integer(), sa.ForeignKey("micro_motives.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_uuid", sa.String(length=36), nullable=False),
        sa.Column("micro_motives", sa.JSON(), nullable=False),
        sa.Column("sjt_answers", sa.JSON(), nullable=False),
        sa.Column("conjoint_choices", sa.JSON(), nullable=False),
        sa.Column("user_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("language_preference", sa.String(length=10), nullable=False, server_default="fa"),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("session_uuid", name="uq_session_uuid"),
    )
    op.create_index("idx_session_created", "user_sessions", ["created_at"])

    op.create_table(
        "discovery_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("major_id", sa.Integer(), sa.ForeignKey("majors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("m_score", sa.Float(), nullable=False),
        sa.Column("s_score", sa.Float(), nullable=False),
        sa.Column("v_score", sa.Float(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("fit_level", sa.String(length=50), nullable=True),
        sa.Column("matched_motives", sa.JSON(), nullable=True),
        sa.Column("strategy_highlights", sa.JSON(), nullable=True),
        sa.Column("value_alignment", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("personalized_description", sa.Text(), nullable=True),
        sa.Column("archetype_info", sa.JSON(), nullable=True),
        sa.Column("alternative_paths", sa.JSON(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "major_id", name="uq_session_major"),
    )
    op.create_index("idx_result_score", "discovery_results", ["total_score"])
    op.create_index("idx_result_session", "discovery_results", ["session_id"])

    op.create_table(
        "branch_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("school_branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("m_score", sa.Float(), nullable=False),
        sa.Column("s_score", sa.Float(), nullable=False),
        sa.Column("v_score", sa.Float(), nullable=False),
        sa.Column("average_score", sa.Float(), nullable=False),
        sa.Column("matched_motives", sa.JSON(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("warning", sa.String(length=500), nullable=True),
        sa.Column("alternative_paths", sa.JSON(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "branch_id", name="uq_session_branch"),
    )
    op.create_index("idx_branch_score", "branch_recommendations", ["average_score"])

    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("satisfaction_score", sa.Integer(), nullable=True),
        sa.Column("accuracy_rating", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("recommended_major_id", sa.Integer(), sa.ForeignKey("majors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("would_recommend", sa.Boolean(), nullable=True),
        sa.Column("contact_for_research", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", name="uq_feedback_session"),
    )
    op.create_index("idx_feedback_created", "user_feedback", ["created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_name", sa.String(length=100), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("changed_by", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_timestamp", "audit_logs", ["created_at"])
    op.create_index("idx_audit_table", "audit_logs", ["table_name"])


def downgrade() -> None:
    op.drop_index("idx_audit_table", table_name="audit_logs")
    op.drop_index("idx_audit_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("idx_feedback_created", table_name="user_feedback")
    op.drop_table("user_feedback")

    op.drop_index("idx_branch_score", table_name="branch_recommendations")
    op.drop_table("branch_recommendations")

    op.drop_index("idx_result_session", table_name="discovery_results")
    op.drop_index("idx_result_score", table_name="discovery_results")
    op.drop_table("discovery_results")

    op.drop_index("idx_session_created", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_table("branch_micro_motives")
    op.drop_table("major_micro_motives")

    op.drop_table("school_branches")

    op.drop_index("idx_major_cluster", table_name="majors")
    op.drop_index("idx_major_group", table_name="majors")
    op.drop_table("majors")

    op.drop_index("idx_question_code", table_name="trait_options")
    op.drop_table("trait_options")

    op.drop_index("idx_value_question", table_name="value_poles")
    op.drop_table("value_poles")

    op.drop_index("idx_motive_category", table_name="micro_motives")
    op.drop_table("micro_motives")
