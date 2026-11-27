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
from referral_service import create_referral_code, get_referral_report
from referral_commission_service import (
    create_code_for_marketer,
    marketer_recruitment_report,
    marketer_statement,
    register_marketer,
    settle_commission,
    signups_of_marketer,
)
from sqlalchemy.exc import IntegrityError

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


def current_referral_manager(actor: User = Depends(current_admin)) -> User:
    """Referral code creation and reporting are restricted to active admins."""
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="manager access required")
    return actor


class GrantRequest(BaseModel):
    user_id: int
    plan_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=1000)


class RevokeRequest(BaseModel):
    entitlement_id: int
    reason: str = Field(min_length=1, max_length=1000)


class ReferralCodeCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=32)


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


@router.post("/referrals/codes", status_code=201)
def create_referral(
    req: ReferralCodeCreateRequest,
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    try:
        record = create_referral_code(db, actor, label=req.label, code=req.code)
        db.commit()
        metadata = record.metadata_json if isinstance(record.metadata_json, dict) else {}
        return {
            "id": int(record.id),
            "code": record.target_id,
            "label": str(metadata.get("label") or ""),
            "is_active": bool(metadata.get("is_active", True)),
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="referral code already exists") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/referrals/report")
def referral_report(
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return get_referral_report(db, actor)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Commission ownership. These endpoints record who owns a code and what each
# paid order owes them; they never move money or touch the credit ledger.
# ---------------------------------------------------------------------------


class MarketerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    user_id: int | None = None
    commission_bps: int = Field(default=0, ge=0, le=10000)
    note: str | None = Field(default=None, max_length=500)


class MarketerCodeRequest(BaseModel):
    marketer_id: int
    code: str | None = Field(default=None, max_length=32)


class CommissionSettleRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


@router.post("/marketers", status_code=201)
def create_marketer(
    req: MarketerCreateRequest,
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    try:
        marketer = register_marketer(
            db,
            actor,
            name=req.name,
            phone=req.phone,
            user_id=req.user_id,
            commission_bps=req.commission_bps,
            note=req.note,
        )
        db.commit()
        return {
            "id": int(marketer.id),
            "public_id": marketer.public_id,
            "name": marketer.name,
            "phone": marketer.phone,
            "user_id": int(marketer.user_id) if marketer.user_id else None,
            "commission_bps": int(marketer.commission_bps),
            "commission_percent": round(int(marketer.commission_bps) / 100, 2),
            "is_active": bool(marketer.is_active),
        }
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/marketers/codes", status_code=201)
def create_marketer_code(
    req: MarketerCodeRequest,
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    try:
        row = create_code_for_marketer(db, actor, marketer_id=req.marketer_id, code=req.code)
        db.commit()
        return {
            "id": int(row.id),
            "code": row.code,
            "marketer_id": int(row.marketer_id),
            "is_active": bool(row.is_active),
        }
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="referral code already exists") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/commission/statement")
def commission_statement(
    marketer_id: int | None = None,
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    """Who is owed what. Reads snapshots only; never recalculates past orders."""
    try:
        return marketer_statement(db, actor, marketer_id=marketer_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/commission/{commission_id}/settle")
def settle(
    commission_id: int,
    req: CommissionSettleRequest | None = None,
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    try:
        row = settle_commission(db, actor, commission_id=commission_id, note=(req.note if req else None))
        db.commit()
        return {
            "id": int(row.id),
            "order_id": int(row.order_id),
            "marketer_id": int(row.marketer_id),
            "amount_minor": int(row.commission_amount_minor),
            "currency": row.currency,
            "status": row.status,
        }
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/marketers/report")
def recruitment_report(
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    """How many people each marketer brought, and what they bought.

    This is the answer to "my marketer says he sent ten people, how do I know?":
    ``signups`` counts registrations carrying his code, independent of purchase.
    """
    try:
        return marketer_recruitment_report(db, actor)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/marketers/{marketer_id}/signups")
def marketer_signups(
    marketer_id: int,
    actor: User = Depends(current_referral_manager),
    db: Session = Depends(get_db),
) -> dict:
    """The actual list of people brought by one marketer."""
    try:
        return signups_of_marketer(db, actor, marketer_id=marketer_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
