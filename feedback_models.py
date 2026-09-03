"""Standalone web-feedback persistence contract.

Feedback is operational/user-submitted data and is intentionally kept separate
from the legacy session-bound UserFeedback table. This lets the public web form
store its five explicit metrics without weakening the existing session schema.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, Index, String, Text
from sqlalchemy.sql import func

from models import Base


class FeedbackSubmission(Base):
    __tablename__ = "feedback_submissions"
    __table_args__ = (Index("idx_feedback_submissions_created", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(36), nullable=True, index=True)
    exam_code = Column(String(64), nullable=True)
    exam_date = Column(String(40), nullable=True)
    suggested_major = Column(String(200), nullable=True)
    suggested_score = Column(Integer, nullable=True)
    major_fit = Column(Integer, nullable=False)
    motive_accuracy = Column(Integer, nullable=False)
    strategy_fit = Column(Integer, nullable=False)
    value_fit = Column(Integer, nullable=False)
    nps = Column(Integer, nullable=False)
    desired_major = Column(String(200), nullable=True)
    comments = Column(Text, nullable=True)
    source = Column(String(32), nullable=False, default="web", server_default="web")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
