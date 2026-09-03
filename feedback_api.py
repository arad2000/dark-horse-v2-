"""Public feedback endpoint for the Dark Horse web application."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from feedback_models import FeedbackSubmission

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    session_uuid: str | None = Field(default=None, min_length=1, max_length=36)
    exam_code: str | None = Field(default=None, max_length=64)
    exam_date: str | None = Field(default=None, max_length=40)
    suggested_major: str | None = Field(default=None, max_length=200)
    suggested_score: int | None = Field(default=None, ge=0, le=100)
    major_fit: int = Field(ge=1, le=5)
    motive_accuracy: int = Field(ge=1, le=5)
    strategy_fit: int = Field(ge=1, le=5)
    value_fit: int = Field(ge=1, le=5)
    nps: int = Field(ge=0, le=10)
    desired_major: str | None = Field(default=None, max_length=200)
    comments: str | None = Field(default=None, max_length=4000)


@router.post("/feedback", status_code=201)
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        row = FeedbackSubmission(
            session_uuid=payload.session_uuid,
            exam_code=payload.exam_code,
            exam_date=payload.exam_date,
            suggested_major=payload.suggested_major,
            suggested_score=payload.suggested_score,
            major_fit=payload.major_fit,
            motive_accuracy=payload.motive_accuracy,
            strategy_fit=payload.strategy_fit,
            value_fit=payload.value_fit,
            nps=payload.nps,
            desired_major=payload.desired_major,
            comments=payload.comments,
            source="web",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"accepted": True, "feedback_id": row.id}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="ثبت بازخورد ناموفق بود") from exc
