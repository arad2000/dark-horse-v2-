"""
SQLAlchemy ORM Models for Dark Horse V2
Database schema definition with relationships
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, JSON, ForeignKey, Table, UniqueConstraint,
    Index, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

# ============================================
# Association Tables (Many-to-Many)
# ============================================

major_micro_motives = Table(
    'major_micro_motives',
    Base.metadata,
    Column('major_id', Integer, ForeignKey('majors.id', ondelete='CASCADE'), primary_key=True),
    Column('motive_id', Integer, ForeignKey('micro_motives.id', ondelete='CASCADE'), primary_key=True),
)

branch_micro_motives = Table(
    'branch_micro_motives',
    Base.metadata,
    Column('branch_id', Integer, ForeignKey('school_branches.id', ondelete='CASCADE'), primary_key=True),
    Column('motive_id', Integer, ForeignKey('micro_motives.id', ondelete='CASCADE'), primary_key=True),
)

# ============================================
# Core Models
# ============================================

class MicroMotive(Base):
    """
    Micro Motives Database
    Represents individual motivations/sparks that drive students
    """
    __tablename__ = "micro_motives"
    __table_args__ = (
        UniqueConstraint('code', name='uq_motive_code'),
        Index('idx_motive_category', 'category'),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)  # e.g., "MED-001"
    description_fa = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)  # e.g., "medical", "engineering"
    intensity_level = Column(Integer, default=1)  # 1-5 scale
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    majors = relationship("Major", secondary=major_micro_motives, back_populates="micro_motives")
    branches = relationship("SchoolBranch", secondary=branch_micro_motives, back_populates="micro_motives")

    def __repr__(self):
        return f"<MicroMotive(code={self.code}, description={self.description_fa[:30]}...)>"


class ValuePole(Base):
    """
    Value Poles / Conjoint Analysis Pairs
    Binary value choices (A vs B pairs)
    """
    __tablename__ = "value_poles"
    __table_args__ = (
        UniqueConstraint('pole_code', name='uq_pole_code'),
    )

    id = Column(Integer, primary_key=True, index=True)
    pole_code = Column(String(10), unique=True, nullable=False)  # e.g., "Q1A", "Q1B"
    question_num = Column(Integer, nullable=False)  # 1-15
    option_letter = Column(String(1), nullable=False)  # "A" or "B"
    description_fa = Column(String(300), nullable=False)
    opposite_pole_id = Column(Integer, ForeignKey('value_poles.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ValuePole(code={self.pole_code}, desc={self.description_fa[:20]}...)>"


class TraitOption(Base):
    """
    Strategy/Trait Mapping for SJT Questions (S01-S25)
    Maps question indices to behavioral traits
    """
    __tablename__ = "trait_options"
    __table_args__ = (
        UniqueConstraint('question_code', 'option_index', name='uq_question_option'),
        Index('idx_question_code', 'question_code'),
    )

    id = Column(Integer, primary_key=True, index=True)
    question_code = Column(String(10), nullable=False)  # e.g., "S01", "S02"
    option_index = Column(Integer, nullable=False)  # 0-4 (for A-E)
    traits = Column(JSON, nullable=True)  # ["trait1", "trait2"]
    description_fa = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TraitOption(question={self.question_code}, option={self.option_index})>"


class Major(Base):
    """
    University Majors Database
    ~160 majors with psychological profiles
    """
    __tablename__ = "majors"
    __table_args__ = (
        UniqueConstraint('name', name='uq_major_name'),
        Index('idx_major_group', 'group'),
        Index('idx_major_cluster', 'cluster'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)  # e.g., "پزشکی"
    group = Column(String(100), nullable=False)  # e.g., "علوم پزشکی"
    cluster = Column(String(10), nullable=True)  # e.g., "A", "B"
    subgroup = Column(String(50), nullable=True)
    exam_group = Column(String(50), nullable=True)  # e.g., "تجربی"
    high_school_branch = Column(String(100), nullable=True)

    # Scoring Weights
    strategy_weights = Column(JSON, nullable=False)  # 25x5 matrix for SJT
    value_weights = Column(JSON, nullable=False)  # 15 Q pairs with A/B weights
    
    # Metadata
    archetype = Column(String(200), nullable=True)  # e.g., "تشخیصگر-نجاتبخش"
    fulfillment_source = Column(Text, nullable=True)  # Story about fulfillment
    prestige_level = Column(Integer, nullable=True)  # Market demand: 1-5 (1=low, 5=high)
    
    # Flags
    handcrafted = Column(Boolean, default=True)  # Manually curated?
    motive_driven = Column(Boolean, default=True)
    weights_version = Column(String(100), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    micro_motives = relationship("MicroMotive", secondary=major_micro_motives, back_populates="majors")
    discovery_results = relationship("DiscoveryResult", back_populates="major", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Major(name={self.name}, group={self.group})>"


class SchoolBranch(Base):
    """
    High School Branches (شاخه‌های دبیرستان)
    ریاضی فیزیک، علوم تجربی، انسانی، هنر
    """
    __tablename__ = "school_branches"
    __table_args__ = (
        UniqueConstraint('name', name='uq_branch_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., "علوم تجربی"
    group = Column(String(50), nullable=False)
    
    # M-Score calculation limit
    m_score_denom_limit = Column(Integer, default=30)
    
    # Scoring Weights
    strategy_weights = Column(JSON, nullable=False)  # 25x5 matrix
    value_weights = Column(JSON, nullable=False)
    
    # Metadata
    weights_version = Column(String(100), nullable=True)
    source_majors_count = Column(Integer, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    micro_motives = relationship("MicroMotive", secondary=branch_micro_motives, back_populates="branches")
    branch_recommendations = relationship("BranchRecommendation", back_populates="branch", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SchoolBranch(name={self.name})>"


# ============================================
# Session & Result Models
# ============================================

class UserSession(Base):
    """
    User Discovery Sessions
    Tracks individual user assessments
    """
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index('idx_session_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(36), unique=True, nullable=False)  # UUID
    
    # User Inputs (JSON for flexibility - can add more fields later)
    micro_motives = Column(JSON, nullable=False)  # List of selected codes
    sjt_answers = Column(JSON, nullable=False)  # {"sjt_1": "A", "sjt_2": "C", ...}
    conjoint_choices = Column(JSON, nullable=False)  # {"conj_1": "Q1A", ...}
    
    # Session Metadata
    user_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    language_preference = Column(String(10), default="fa")
    
    # Status
    is_completed = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    discovery_results = relationship("DiscoveryResult", back_populates="session", cascade="all, delete-orphan")
    branch_recommendations = relationship("BranchRecommendation", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("UserFeedback", back_populates="session", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserSession(uuid={self.session_uuid[:8]}..., created={self.created_at})>"


class DiscoveryResult(Base):
    """
    Major Discovery Results
    One record per (session, major) pair
    """
    __tablename__ = "discovery_results"
    __table_args__ = (
        UniqueConstraint('session_id', 'major_id', name='uq_session_major'),
        Index('idx_result_score', 'total_score'),
        Index('idx_result_session', 'session_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('user_sessions.id', ondelete='CASCADE'), nullable=False)
    major_id = Column(Integer, ForeignKey('majors.id', ondelete='CASCADE'), nullable=False)
    
    # Score Components
    m_score = Column(Float, nullable=False)  # 0-1, motive alignment
    s_score = Column(Float, nullable=False)  # 0-1, strategy alignment
    v_score = Column(Float, nullable=False)  # 0-1, value alignment
    total_score = Column(Float, nullable=False, index=True)  # 0-100
    fit_level = Column(String(50), nullable=True)  # "همخوانی بسیار بالا"
    
    # Evidence & Reasoning
    matched_motives = Column(JSON, nullable=True)  # [{"code": "MED-001", "desc": "..."}, ...]
    strategy_highlights = Column(JSON, nullable=True)
    value_alignment = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    personalized_description = Column(Text, nullable=True)
    
    # Related Information
    archetype_info = Column(JSON, nullable=True)  # {archetype, fulfillment_source, traits, values}
    alternative_paths = Column(JSON, nullable=True)  # Top 3 similar majors
    
    # Rank in results
    rank = Column(Integer, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("UserSession", back_populates="discovery_results")
    major = relationship("Major", back_populates="discovery_results")

    def __repr__(self):
        return f"<DiscoveryResult(major={self.major.name if self.major else 'N/A'}, score={self.total_score})>"


class BranchRecommendation(Base):
    """
    School Branch Recommendations
    Results for شاخه‌های دبیرستان guidance
    """
    __tablename__ = "branch_recommendations"
    __table_args__ = (
        UniqueConstraint('session_id', 'branch_id', name='uq_session_branch'),
        Index('idx_branch_score', 'average_score'),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('user_sessions.id', ondelete='CASCADE'), nullable=False)
    branch_id = Column(Integer, ForeignKey('school_branches.id', ondelete='CASCADE'), nullable=False)
    
    # Score Components
    m_score = Column(Float, nullable=False)
    s_score = Column(Float, nullable=False)
    v_score = Column(Float, nullable=False)
    average_score = Column(Float, nullable=False, index=True)
    
    # Evidence
    matched_motives = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    warning = Column(String(500), nullable=True)
    alternative_paths = Column(JSON, nullable=True)
    
    # Rank
    rank = Column(Integer, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("UserSession", back_populates="branch_recommendations")
    branch = relationship("SchoolBranch", back_populates="branch_recommendations")

    def __repr__(self):
        return f"<BranchRecommendation(branch={self.branch.name if self.branch else 'N/A'}, score={self.average_score})>"


class UserFeedback(Base):
    """
    User Feedback on Results
    للتحسين المستمر - Continuous improvement
    """
    __tablename__ = "user_feedback"
    __table_args__ = (
        Index('idx_feedback_created', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('user_sessions.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Feedback
    satisfaction_score = Column(Integer, nullable=True)  # 1-5
    accuracy_rating = Column(Integer, nullable=True)  # 1-5, how accurate were results?
    comments = Column(Text, nullable=True)
    recommended_major_id = Column(Integer, ForeignKey('majors.id', ondelete='SET NULL'), nullable=True)
    
    # Follow-up
    would_recommend = Column(Boolean, nullable=True)
    contact_for_research = Column(Boolean, default=False)
    email = Column(String(255), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("UserSession", back_populates="feedback")

    def __repr__(self):
        return f"<UserFeedback(session_id={self.session_id}, satisfaction={self.satisfaction_score})>"


class AuditLog(Base):
    """
    Audit Trail for Data Changes
    Track who changed what and when
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('idx_audit_timestamp', 'created_at'),
        Index('idx_audit_table', 'table_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)  # "INSERT", "UPDATE", "DELETE"
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changed_by = Column(String(100), nullable=True)  # System user or IP
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AuditLog(table={self.table_name}, action={self.action}, id={self.record_id})>"
