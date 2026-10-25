"""Admin API router mounted on the commercial Liara deploy.

Operational-only: grant/revoke credits, dashboard counts, user list, feedback.
Does not touch scoring or reference JSON datasets.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from admin_api import admin_grant_credits, admin_revoke_entitlement, dashboard_summary, list_feedback
from admin_service import list_user_summary
from auth_service import resolve_session
from billing_models import User
from database import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def current_admin(
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
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if user.role not in {"admin", "support"} or user.status != "active":
        raise HTTPException(status_code=403, detail="admin access required")
    return user


class GrantRequest(BaseModel):
    user_id: int
    plan_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=1000)


class RevokeRequest(BaseModel):
    entitlement_id: int
    reason: str = Field(min_length=1, max_length=1000)


@router.get("/dashboard")
def get_dashboard(actor: User = Depends(current_admin), db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        return dashboard_summary(db, actor)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/users")
def list_users(
    limit: int = 50,
    actor: User = Depends(current_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    try:
        return list_user_summary(db, actor, limit=limit)
    except (PermissionError, ValueError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/feedback")
def get_feedback(
    limit: int = 50,
    actor: User = Depends(current_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    try:
        return list_feedback(db, actor, limit=limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/credits/grant")
def grant(req: GrantRequest, actor: User = Depends(current_admin), db: Session = Depends(get_db)) -> dict:
    try:
        result = admin_grant_credits(
            db,
            actor,
            user_id=req.user_id,
            plan_code=req.plan_code,
            reason=req.reason,
        )
        db.commit()
        return result
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/credits/revoke")
def revoke(req: RevokeRequest, actor: User = Depends(current_admin), db: Session = Depends(get_db)) -> dict:
    try:
        result = admin_revoke_entitlement(
            db,
            actor,
            entitlement_id=req.entitlement_id,
            reason=req.reason,
        )
        db.commit()
        return result
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
