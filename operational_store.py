"""Dark Horse V2 — operational persistence service for the Hybrid architecture.

This module persists only operational/user data. It never selects PostgreSQL as the
scoring source and never mutates reference JSON. It is deliberately usable while
POSTGRES_RUNTIME_CUTOVER_APPROVED remains False.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    AuditLog,
    BranchRecommendation,
    DiscoveryResult,
    Major,
    SchoolBranch,
    UserFeedback,
    UserSession,
)


class OperationalStore:
    """Transactional store for sessions, results, recommendations and feedback."""

    def __init__(self, session_factory=SessionLocal):
        if session_factory is None:
            raise RuntimeError("DATABASE_URL is not configured")
        self._session_factory = session_factory

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """Yield a session and commit atomically; rollback on any exception."""
        db = self._session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_session(
        self,
        micro_motives: list[str],
        sjt_answers: dict[str, Any],
        conjoint_choices: dict[str, Any],
        *,
        session_uuid: str | None = None,
        user_ip: str | None = None,
        user_agent: str | None = None,
        language_preference: str = "fa",
    ) -> UserSession:
        with self.transaction() as db:
            row = UserSession(
                session_uuid=session_uuid or str(uuid4()),
                micro_motives=micro_motives,
                sjt_answers=sjt_answers,
                conjoint_choices=conjoint_choices,
                user_ip=user_ip,
                user_agent=user_agent,
                language_preference=language_preference,
            )
            db.add(row)
            db.flush()
            db.expunge(row)
            return row

    def store_discovery_results(
        self,
        session_id: int,
        recommendations: list[dict[str, Any]],
    ) -> list[DiscoveryResult]:
        """Persist a deterministic set of major results for an existing session."""
        with self.transaction() as db:
            session = db.get(UserSession, session_id)
            if session is None:
                raise ValueError(f"Unknown session_id: {session_id}")

            rows: list[DiscoveryResult] = []
            for rank, item in enumerate(recommendations, start=1):
                major_id = int(item["major_id"])
                if db.get(Major, major_id) is None:
                    raise ValueError(f"Unknown major_id: {major_id}")
                fit = item.get("individuality_fit", item)
                raw = fit.get("raw_components", {})
                row = DiscoveryResult(
                    session_id=session_id,
                    major_id=major_id,
                    m_score=float(raw.get("m_score", fit.get("m_score", 0.0))),
                    s_score=float(raw.get("s_score", fit.get("s_score", 0.0))),
                    v_score=float(raw.get("v_score", fit.get("v_score", 0.0))),
                    total_score=float(fit.get("score", item.get("fit_score", 0.0))),
                    fit_level=fit.get("level", item.get("fit_level")),
                    matched_motives=fit.get("matched_motives"),
                    strategy_highlights=fit.get("strategy_highlights"),
                    value_alignment=fit.get("value_alignment"),
                    warnings=fit.get("warnings"),
                    personalized_description=fit.get("personalized_description"),
                    archetype_info=fit.get("archetype"),
                    alternative_paths=fit.get("alternative_paths"),
                    rank=rank,
                )
                db.add(row)
                rows.append(row)

            db.flush()
            for row in rows:
                db.expunge(row)
            return rows

    def store_branch_recommendations(
        self,
        session_id: int,
        branches: list[dict[str, Any]],
    ) -> list[BranchRecommendation]:
        with self.transaction() as db:
            session = db.get(UserSession, session_id)
            if session is None:
                raise ValueError(f"Unknown session_id: {session_id}")

            branch_by_name = {b.name: b for b in db.query(SchoolBranch).all()}
            rows: list[BranchRecommendation] = []
            for rank, item in enumerate(branches, start=1):
                name = str(item.get("branch_name") or item.get("branch_name_fa") or "").strip()
                branch = branch_by_name.get(name)
                if branch is None:
                    raise ValueError(f"Unknown school branch: {name}")
                components = item.get("avg_components", {})
                row = BranchRecommendation(
                    session_id=session_id,
                    branch_id=branch.id,
                    m_score=float(components.get("m_score", item.get("m_score", 0.0))),
                    s_score=float(components.get("s_score", item.get("s_score", 0.0))),
                    v_score=float(components.get("v_score", item.get("v_score", 0.0))),
                    average_score=float(item.get("average_score", item.get("fit_score", 0.0))),
                    matched_motives=item.get("matched_motives"),
                    evidence=item.get("evidence"),
                    warning=item.get("warning"),
                    alternative_paths=item.get("alternative_paths"),
                    rank=rank,
                )
                db.add(row)
                rows.append(row)

            db.flush()
            for row in rows:
                db.expunge(row)
            return rows

    def complete_session(self, session_id: int) -> None:
        with self.transaction() as db:
            session = db.get(UserSession, session_id)
            if session is None:
                raise ValueError(f"Unknown session_id: {session_id}")
            session.is_completed = True

    def save_feedback(
        self,
        session_id: int,
        *,
        satisfaction_score: int | None = None,
        accuracy_rating: int | None = None,
        comments: str | None = None,
        recommended_major_id: int | None = None,
        would_recommend: bool | None = None,
        contact_for_research: bool = False,
        email: str | None = None,
    ) -> UserFeedback:
        with self.transaction() as db:
            if db.get(UserSession, session_id) is None:
                raise ValueError(f"Unknown session_id: {session_id}")
            if recommended_major_id is not None and db.get(Major, recommended_major_id) is None:
                raise ValueError(f"Unknown major_id: {recommended_major_id}")
            row = db.query(UserFeedback).filter(UserFeedback.session_id == session_id).one_or_none()
            if row is None:
                row = UserFeedback(session_id=session_id)
                db.add(row)
            row.satisfaction_score = satisfaction_score
            row.accuracy_rating = accuracy_rating
            row.comments = comments
            row.recommended_major_id = recommended_major_id
            row.would_recommend = would_recommend
            row.contact_for_research = contact_for_research
            row.email = email
            db.flush()
            db.expunge(row)
            return row

    def archive_session(self, session_id: int, changed_by: str = "system") -> None:
        with self.transaction() as db:
            session = db.get(UserSession, session_id)
            if session is None:
                raise ValueError(f"Unknown session_id: {session_id}")
            old = {"is_archived": session.is_archived}
            session.is_archived = True
            db.add(
                AuditLog(
                    table_name="user_sessions",
                    record_id=session_id,
                    action="archive",
                    old_values=old,
                    new_values={"is_archived": True},
                    changed_by=changed_by,
                )
            )
