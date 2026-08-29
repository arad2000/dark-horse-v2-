"""Protected Admin API facade over the staged admin service.

This module is intentionally standalone: it does not alter main_v2.py, scoring,
reference JSON, or production deployment state. Callers must resolve the actor
from the existing authentication layer before invoking these functions.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from admin_service import grant_credits, list_user_summary, revoke_entitlement
from billing_models import User


def dashboard_summary(db: Session, actor: User) -> dict:
    """Return a conservative operational dashboard summary."""
    users = list_user_summary(db, actor, limit=500)
    return {
        "users_total": len(users),
        "users_active": sum(1 for item in users if item["status"] == "active"),
        "users_suspended": sum(1 for item in users if item["status"] == "suspended"),
        "note": "Operational summary only; no scoring/reference-data editing.",
    }


def admin_grant_credits(
    db: Session,
    actor: User,
    *,
    user_id: int,
    plan_code: str,
    reason: str,
) -> dict:
    entitlement = grant_credits(db, actor, user_id=user_id, plan_code=plan_code, reason=reason)
    return {
        "entitlement_id": entitlement.id,
        "user_id": entitlement.user_id,
        "plan_id": entitlement.plan_id,
        "credits_granted": entitlement.credits_granted,
        "credits_remaining": entitlement.credits_remaining,
        "status": entitlement.status,
    }


def admin_revoke_entitlement(
    db: Session,
    actor: User,
    *,
    entitlement_id: int,
    reason: str,
) -> dict:
    entitlement = revoke_entitlement(db, actor, entitlement_id=entitlement_id, reason=reason)
    return {
        "entitlement_id": entitlement.id,
        "status": entitlement.status,
        "credits_remaining": entitlement.credits_remaining,
    }
