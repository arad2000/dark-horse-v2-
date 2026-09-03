"""Mounted Admin HTTP router for the production integration branch.

This surface is operational-only: RBAC, billing/user operations, and feedback
analytics. It never exposes or mutates psychometric/reference data.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from admin_api import admin_grant_credits, admin_revoke_entitlement, dashboard_summary
from admin_service import list_user_summary
from auth_service import resolve_session
from billing_models import User
from database import get_db
from feedback_models import FeedbackSubmission

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class GrantRequest(BaseModel):
    user_id: int
    plan_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=1000)


class RevokeRequest(BaseModel):
    entitlement_id: int
    reason: str = Field(min_length=1, max_length=1000)


def _current_admin(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        user = resolve_session(db, token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid or expired session") from exc
    if user.role not in {"admin", "support"} or user.status != "active":
        raise HTTPException(status_code=403, detail="admin access required")
    return user


@router.get("/dashboard")
def get_dashboard(user: User = Depends(_current_admin), db: Session = Depends(get_db)) -> dict[str, int]:
    result = dashboard_summary(db, user)
    result["feedback_total"] = int(db.scalar(select(func.count(FeedbackSubmission.id))) or 0)
    return result


@router.get("/users")
def get_users(
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = list_user_summary(db, user, limit=limit)
    return {
        "users": [
            {
                "public_id": row["public_id"],
                "name": row["name"],
                "status": row["status"],
                "role": row["role"],
            }
            for row in rows
        ]
    }


@router.get("/feedback")
def get_feedback(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = db.scalars(
        select(FeedbackSubmission).order_by(FeedbackSubmission.id.desc()).limit(limit)
    ).all()
    return {
        "feedback": [
            {
                "id": row.id,
                "session_uuid": row.session_uuid,
                "exam_code": row.exam_code,
                "exam_date": row.exam_date,
                "suggested_major": row.suggested_major,
                "suggested_score": row.suggested_score,
                "major_fit": row.major_fit,
                "motive_accuracy": row.motive_accuracy,
                "strategy_fit": row.strategy_fit,
                "value_fit": row.value_fit,
                "nps": row.nps,
                "desired_major": row.desired_major,
                "comments": row.comments,
                "created_at": row.created_at.isoformat() if isinstance(row.created_at, datetime) else row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/credits/grant")
def grant(req: GrantRequest, user: User = Depends(_current_admin), db: Session = Depends(get_db)) -> dict[str, int | str]:
    try:
        result = admin_grant_credits(db, user, user_id=req.user_id, plan_code=req.plan_code, reason=req.reason)
        db.commit()
        return result
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/entitlements/revoke")
def revoke(req: RevokeRequest, user: User = Depends(_current_admin), db: Session = Depends(get_db)) -> dict[str, int | str]:
    try:
        result = admin_revoke_entitlement(db, user, entitlement_id=req.entitlement_id, reason=req.reason)
        db.commit()
        return result
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
