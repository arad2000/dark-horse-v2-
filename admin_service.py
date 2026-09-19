"""Staged admin service for Dark Horse V2.

Admin operations are operational-only. They must never mutate reference/psychometric
source data or scoring logic. Every mutation requires an audit record and a reason.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from billing_models import AdminAuditLog, Entitlement, PremiumPlan, User

ADMIN_ROLES = {"admin", "support"}


def require_admin(actor: User) -> None:
    if actor is None or actor.status != "active" or actor.role not in ADMIN_ROLES:
        raise PermissionError("admin access required")


def _audit(db: Session, actor: User, *, action: str, target_type: str, target_id: str, reason: str) -> None:
    if not reason or not reason.strip():
        raise ValueError("reason is required")
    db.add(
        AdminAuditLog(
            admin_user_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json={"reason": reason.strip()},
        )
    )


def grant_credits(db: Session, actor: User, *, user_id: int, plan_code: str, reason: str) -> Entitlement:
    require_admin(actor)
    user = db.get(User, user_id)
    plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == plan_code, PremiumPlan.is_active.is_(True)))
    if user is None or user.status != "active" or plan is None:
        raise ValueError("unknown/inactive user or inactive plan")
    if plan.credits_granted <= 0 or plan.plan_type != "credits":
        raise ValueError("plan does not grant credits")

    entitlement = Entitlement(
        user_id=user.id,
        plan_id=plan.id,
        source="admin",
        credits_granted=plan.credits_granted,
        credits_remaining=plan.credits_granted,
        starts_at=datetime.now(timezone.utc),
        expires_at=None,
        status="active",
        order_id=None,
    )
    db.add(entitlement)
    db.flush()
    _audit(db, actor, action="grant_credits", target_type="user", target_id=str(user.id), reason=reason)
    return entitlement


def revoke_entitlement(db: Session, actor: User, *, entitlement_id: int, reason: str) -> Entitlement:
    require_admin(actor)
    entitlement = db.get(Entitlement, entitlement_id)
    if entitlement is None:
        raise ValueError("unknown entitlement")
    entitlement.status = "revoked"
    entitlement.credits_remaining = 0
    db.flush()
    _audit(db, actor, action="revoke_entitlement", target_type="entitlement", target_id=str(entitlement.id), reason=reason)
    return entitlement


def list_user_summary(db: Session, actor: User, *, limit: int = 100) -> list[dict]:
    require_admin(actor)
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    users = db.scalars(select(User).order_by(User.id.desc()).limit(limit)).all()
    return [
        {
            "public_id": user.public_id,
            "name": user.name,
            "phone": user.phone,
            "status": user.status,
            "role": user.role,
        }
        for user in users
    ]
