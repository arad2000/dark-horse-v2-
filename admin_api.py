"""Staged Admin API facade.

Operational-only facade over admin_service. Reference/psychometric source data
and scoring logic are intentionally outside this API boundary.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from admin_service import grant_credits, revoke_entitlement, require_admin
from billing_models import AdminAuditLog, Entitlement, Order, Payment, PremiumPlan, User
from models import UserFeedback, UserSession


def dashboard_summary(db: Session, actor: User) -> dict[str, int]:
    require_admin(actor)
    return {
        "users_total": int(db.scalar(select(func.count(User.id))) or 0),
        "orders_total": int(db.scalar(select(func.count(Order.id))) or 0),
        "payments_total": int(db.scalar(select(func.count(Payment.id))) or 0),
        "entitlements_total": int(db.scalar(select(func.count(Entitlement.id))) or 0),
        "audit_logs_total": int(db.scalar(select(func.count(AdminAuditLog.id))) or 0),
        "active_plans_total": int(
            db.scalar(select(func.count(PremiumPlan.id)).where(PremiumPlan.is_active.is_(True))) or 0
        ),
        "feedback_total": int(db.scalar(select(func.count(UserFeedback.id))) or 0),
    }


def list_feedback(db: Session, actor: User, *, limit: int = 50) -> list[dict]:
    require_admin(actor)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")

    rows = db.scalars(
        select(UserFeedback).order_by(UserFeedback.created_at.desc()).limit(limit)
    ).all()

    out: list[dict] = []
    for row in rows:
        session = db.get(UserSession, row.session_id)
        conjoint = (session.conjoint_choices if session else None) or {}
        out.append(
            {
                "id": int(row.id),
                "session_id": int(row.session_id),
                "session_uuid": getattr(session, "session_uuid", None),
                "satisfaction_score": row.satisfaction_score,
                "accuracy_rating": row.accuracy_rating,
                "would_recommend": row.would_recommend,
                "contact_for_research": bool(row.contact_for_research),
                "email": row.email,
                "comments": row.comments,
                "exam_code": conjoint.get("exam_code") if isinstance(conjoint, dict) else None,
                "suggested_major": conjoint.get("suggested_major") if isinstance(conjoint, dict) else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out


def admin_grant_credits(
    db: Session,
    actor: User,
    *,
    user_id: int,
    plan_code: str,
    reason: str,
) -> dict[str, int | str]:
    entitlement = grant_credits(
        db,
        actor,
        user_id=user_id,
        plan_code=plan_code,
        reason=reason,
    )
    return {
        "entitlement_id": int(entitlement.id),
        "credits_granted": int(entitlement.credits_granted),
        "credits_remaining": int(entitlement.credits_remaining),
        "status": entitlement.status,
    }


def admin_revoke_entitlement(
    db: Session,
    actor: User,
    *,
    entitlement_id: int,
    reason: str,
) -> dict[str, int | str]:
    entitlement = revoke_entitlement(
        db,
        actor,
        entitlement_id=entitlement_id,
        reason=reason,
    )
    return {
        "entitlement_id": int(entitlement.id),
        "credits_remaining": int(entitlement.credits_remaining),
        "status": entitlement.status,
    }
