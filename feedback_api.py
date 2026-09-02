"""Public feedback API for Dark Horse V2.

Collects post-journey ratings for product optimization. Does not affect
live scoring formulas. Creates a minimal operational session so feedback
can attach to the hybrid UserFeedback table.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    exam_code: str | None = None
    exam_date: str | None = None
    suggested_major: str | None = None
    suggested_score: float | None = None
    major_fit: int | None = Field(default=None, ge=1, le=5)
    motive_accuracy: int | None = Field(default=None, ge=1, le=5)
    strategy_fit: int | None = Field(default=None, ge=1, le=5)
    value_fit: int | None = Field(default=None, ge=1, le=5)
    nps: int | None = Field(default=None, ge=0, le=10)
    desired_major: str | None = None
    comments: str | None = None
    submitted_at: str | None = None
    email: str | None = None
    contact_for_research: bool = False


def _clamp_1_5(value: int | None) -> int | None:
    if value is None:
        return None
    return max(1, min(5, int(value)))


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest) -> dict[str, Any]:
    """Store feedback for later analysis / system optimization."""
    try:
        from database import is_configured
        from operational_store import OperationalStore

        if not is_configured():
            raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")

        ratings = [r for r in (req.major_fit, req.motive_accuracy, req.strategy_fit, req.value_fit) if r is not None]
        satisfaction = _clamp_1_5(req.major_fit)
        accuracy = _clamp_1_5(int(round(sum(ratings) / len(ratings))) if ratings else None)

        payload = req.model_dump()
        comment_parts: list[str] = []
        if req.comments:
            comment_parts.append(req.comments.strip())
        if req.desired_major:
            comment_parts.append(f"desired_major={req.desired_major.strip()}")
        if req.suggested_major:
            comment_parts.append(f"suggested_major={req.suggested_major}")
        if req.nps is not None:
            comment_parts.append(f"nps={req.nps}")
        # Keep structured copy for optimization pipelines.
        comment_parts.append("payload=" + json.dumps(payload, ensure_ascii=False))
        comments = " | ".join(comment_parts)[:4000]

        store = OperationalStore()
        session = store.create_session(
            micro_motives=["FEEDBACK_ONLY"],
            sjt_answers={},
            conjoint_choices={
                "source": "feedback_form",
                "exam_code": req.exam_code,
                "suggested_major": req.suggested_major,
            },
            session_uuid=str(uuid4()),
        )
        row = store.save_feedback(
            session.id,
            satisfaction_score=satisfaction,
            accuracy_rating=accuracy,
            comments=comments,
            would_recommend=(req.nps is not None and req.nps >= 7),
            contact_for_research=bool(req.contact_for_research),
            email=(req.email or None),
        )
        return {
            "ok": True,
            "feedback_id": row.id,
            "session_id": session.id,
            "session_uuid": session.session_uuid,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"feedback save failed: {exc}") from exc


@router.get("/feedback/health")
def feedback_health() -> dict[str, str]:
    return {"status": "ok", "endpoint": "/api/v1/feedback"}
