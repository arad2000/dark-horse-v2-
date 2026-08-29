"""Staged Admin API facade.

Operational-only facade over admin_service. Reference/psychometric source data
and scoring logic are intentionally outside this API boundary.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from admin_service import grant_credits, revoke_entitlement, require_admin
from billing_models import AdminAuditLog, Entitlement, Order, Payment, PremiumPlan, User


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
    }


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
