"""Dark Horse V2 — SQLAlchemy models for the Hybrid data layer.

Reference/psychometric data remains versioned in JSON under Git.
Operational user/session/result data is modeled for PostgreSQL.
No scoring or recommendation logic lives in this module.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

major_micro_motives = Table(
    "major_micro_motives",
    Base.metadata,
    Column("major_id", Integer, ForeignKey("majors.id", ondelete="CASCADE"), primary_key=True),
    Column("motive_id", Integer, ForeignKey("micro_motives.id", ondelete="CASCADE"), primary_key=True),
)

branch_micro_motives = Table(
    "branch_micro_motives",
    Base.metadata,
    Column("branch_id", Integer, ForeignKey("school_branches.id", ondelete="CASCADE"), primary_key=True),
    Column("motive_id", Integer, ForeignKey("micro_motives.id", ondelete="CASCADE"), primary_key=True),
)


class MicroMotive(Base):
    __tablename__ = "micro_motives"
    __table_args__ = (UniqueConstraint("code", name="uq_motive_code"), Index("idx_motive_category", "category"))

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), nullable=False, unique=True)
    description_fa = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)
    intensity_level = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    majors = relationship("Major", secondary=major_micro_motives, back_populates="micro_motives")
    branches = relationship("SchoolBranch", secondary=branch_micro_motives, back_populates="micro_motives")


class ValuePole(Base):
    __tablename__ = "value_poles"
    __table_args__ = (UniqueConstraint("pole_code", name="uq_pole_code"), Index("idx_value_question", "question_num"))

    id = Column(Integer, primary_key=True, index=True)
    pole_code = Column(String(16), nullable=False, unique=True)
    question_num = Column(Integer, nullable=False)
    option_letter = Column(String(1), nullable=False)
    description_fa = Column(String(300), nullable=False)
    opposite_pole_id = Column(Integer, ForeignKey("value_poles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TraitOption(Base):
    __tablename__ = "trait_options"
    __table_args__ = (
        UniqueConstraint("question_code", "option_index", name="uq_question_option"),
        Index("idx_question_code", "question_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    question_code = Column(String(10), nullable=False)
    option_index = Column(Integer, nullable=False)
    traits = Column(JSON, nullable=True)
    description_fa = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Major(Base):
    __tablename__ = "majors"
    __table_args__ = (
        UniqueConstraint("name", name="uq_major_name"),
        Index("idx_major_group", "group"),
        Index("idx_major_cluster", "cluster"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    group = Column(String(100), nullable=False)
    cluster = Column(String(20), nullable=True)
    subgroup = Column(String(80), nullable=True)
    exam_group = Column(String(80), nullable=True)
    high_school_branch = Column(String(100), nullable=True)
    strategy_weights = Column(JSON, nullable=False)
    value_weights = Column(JSON, nullable=False)
    archetype = Column(String(200), nullable=True)
    fulfillment_source = Column(Text, nullable=True)
    prestige_level = Column(Integer, nullable=True)
    handcrafted = Column(Boolean, default=True, nullable=False)
    motive_driven = Column(Boolean, default=True, nullable=False)
    weights_version = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    micro_motives = relationship("MicroMotive", secondary=major_micro_motives, back_populates="majors")
    discovery_results = relationship("DiscoveryResult", back_populates="major", cascade="all, delete-orphan")


class SchoolBranch(Base):
    __tablename__ = "school_branches"
    __table_args__ = (UniqueConstraint("name", name="uq_branch_name"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    group = Column(String(50), nullable=False)
    m_score_denom_limit = Column(Integer, default=30, nullable=False)
    strategy_weights = Column(JSON, nullable=False)
    value_weights = Column(JSON, nullable=False)
    weights_version = Column(String(100), nullable=True)
    source_majors_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    micro_motives = relationship("MicroMotive", secondary=branch_micro_motives, back_populates="branches")
    branch_recommendations = relationship("BranchRecommendation", back_populates="branch", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (Index("idx_session_created", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(36), nullable=False, unique=True)
    micro_motives = Column(JSON, nullable=False)
    sjt_answers = Column(JSON, nullable=False)
    conjoint_choices = Column(JSON, nullable=False)
    user_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    language_preference = Column(String(10), default="fa", nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    discovery_results = relationship("DiscoveryResult", back_populates="session", cascade="all, delete-orphan")
    branch_recommendations = relationship("BranchRecommendation", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("UserFeedback", back_populates="session", uselist=False, cascade="all, delete-orphan")


class DiscoveryResult(Base):
    __tablename__ = "discovery_results"
    __table_args__ = (
        UniqueConstraint("session_id", "major_id", name="uq_session_major"),
        Index("idx_result_score", "total_score"),
        Index("idx_result_session", "session_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False)
    major_id = Column(Integer, ForeignKey("majors.id", ondelete="CASCADE"), nullable=False)
    m_score = Column(Float, nullable=False)
    s_score = Column(Float, nullable=False)
    v_score = Column(Float, nullable=False)
    total_score = Column(Float, nullable=False, index=True)
    fit_level = Column(String(50), nullable=True)
    matched_motives = Column(JSON, nullable=True)
    strategy_highlights = Column(JSON, nullable=True)
    value_alignment = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    personalized_description = Column(Text, nullable=True)
    archetype_info = Column(JSON, nullable=True)
    alternative_paths = Column(JSON, nullable=True)
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("UserSession", back_populates="discovery_results")
    major = relationship("Major", back_populates="discovery_results")


class BranchRecommendation(Base):
    __tablename__ = "branch_recommendations"
    __table_args__ = (
        UniqueConstraint("session_id", "branch_id", name="uq_session_branch"),
        Index("idx_branch_score", "average_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("school_branches.id", ondelete="CASCADE"), nullable=False)
    m_score = Column(Float, nullable=False)
    s_score = Column(Float, nullable=False)
    v_score = Column(Float, nullable=False)
    average_score = Column(Float, nullable=False, index=True)
    matched_motives = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    warning = Column(String(500), nullable=True)
    alternative_paths = Column(JSON, nullable=True)
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("UserSession", back_populates="branch_recommendations")
    branch = relationship("SchoolBranch", back_populates="branch_recommendations")


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (Index("idx_feedback_created", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    satisfaction_score = Column(Integer, nullable=True)
    accuracy_rating = Column(Integer, nullable=True)
    comments = Column(Text, nullable=True)
    recommended_major_id = Column(Integer, ForeignKey("majors.id", ondelete="SET NULL"), nullable=True)
    would_recommend = Column(Boolean, nullable=True)
    contact_for_research = Column(Boolean, default=False, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("UserSession", back_populates="feedback")
    recommended_major = relationship("Major", foreign_keys=[recommended_major_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("idx_audit_timestamp", "created_at"), Index("idx_audit_table", "table_name"))

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
