"""Referral attribution for paid orders.

Referral tracking is deliberately limited to attribution snapshots and reporting.
It does not calculate commissions, balances, payouts, wallets, or settlements.
"""
from __future__ import annotations

import re
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from billing_models import AdminAuditLog, Order, ReferralCode, User

_CODE_PATTERN = re.compile(r"^[A-Z0-9]{4,32}$")
_CODE_ALPHABET = string.ascii_uppercase + string.digits


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_manager(actor: User | None) -> None:
    # Referral-code administration and reports are manager-only.
    if actor is None or actor.status != "active" or actor.role != "admin":
        raise PermissionError("active manager access required")


def _normalize_user_code(value: str | None) -> tuple[str | None, bool]:
    raw = (value or "").strip()
    if not raw:
        return None, False
    candidate = raw.upper()
    if not _CODE_PATTERN.fullmatch(candidate):
        return None, True
    return candidate, False


def create_referral_code(
    db: Session,
    actor: User,
    *,
    label: str,
    code: str | None = None,
) -> ReferralCode:
    """Create one manager-owned attribution code; generated when omitted."""
    _require_manager(actor)
    clean_label = (label or "").strip()
    if not clean_label or len(clean_label) > 200:
        raise ValueError("label must contain 1 to 200 characters")

    requested = (code or "").strip()
    if requested:
        normalized = requested.upper()
        if not _CODE_PATTERN.fullmatch(normalized):
            raise ValueError("code must contain 4 to 32 ASCII letters or digits")
        if db.scalar(select(ReferralCode.id).where(ReferralCode.code == normalized)) is not None:
            raise ValueError("referral code already exists")
    else:
        normalized = ""
        for _ in range(10):
            candidate = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(10))
            exists = db.scalar(select(ReferralCode.id).where(ReferralCode.code == candidate))
            if exists is None:
                normalized = candidate
                break
        if not normalized:
            raise RuntimeError("could not allocate a unique referral code")

    record = ReferralCode(
        code=normalized,
        label=clean_label,
        is_active=True,
        created_by_user_id=int(actor.id),
    )
    db.add(record)
    db.flush()
    db.add(
        AdminAuditLog(
            admin_user_id=int(actor.id),
            action="create_referral_code",
            target_type="referral_code",
            target_id=str(record.id),
            metadata_json={"label": clean_label, "generated": not bool(requested)},
        )
    )
    db.flush()
    return record


def set_user_referral_code(
    db: Session,
    *,
    user_id: int,
    code: str | None,
) -> dict[str, object]:
    """Set or clear a user's referral attribution before their first paid order.

    Empty and invalid codes both resolve to direct attribution. An invalid code
    is intentionally non-blocking: a user can continue buying without a code.
    """
    user_stmt = select(User).where(User.id == int(user_id)).with_for_update()
    user = db.scalar(user_stmt)
    if user is None:
        raise ValueError("unknown user")

    already_paid = db.scalar(
        select(Order.id)
        .where(
            Order.user_id == user.id,
            Order.status == "paid",
            Order.paid_at.is_not(None),
        )
        .limit(1)
    )
    if user.referral_locked_at is not None or already_paid is not None:
        raise PermissionError("referral attribution is locked after the first successful payment")

    normalized, malformed = _normalize_user_code(code)
    if normalized is None:
        user.referral_code = None
        db.flush()
        return {
            "status": "invalid_ignored" if malformed else "direct",
            "applied": False,
            "purchase_allowed": True,
            "referral_code": None,
        }

    record = db.scalar(
        select(ReferralCode).where(
            ReferralCode.code == normalized,
            ReferralCode.is_active.is_(True),
        )
    )
    if record is None:
        user.referral_code = None
        db.flush()
        return {
            "status": "invalid_ignored",
            "applied": False,
            "purchase_allowed": True,
            "referral_code": None,
        }

    user.referral_code = record.code
    db.flush()
    return {
        "status": "applied",
        "applied": True,
        "purchase_allowed": True,
        "referral_code": record.code,
        "label": record.label,
    }


def snapshot_order_referral(
    db: Session,
    order: Order,
    *,
    paid_at: datetime,
) -> None:
    """Freeze the current account attribution on the order in the payment transaction."""
    if order.referral_snapshot_at is not None:
        return

    user = db.scalar(
        select(User).where(User.id == order.user_id).with_for_update()
    )
    if user is None:
        raise ValueError("order user not found")

    previous_paid_order = db.scalar(
        select(Order)
        .where(
            Order.user_id == user.id,
            Order.id != order.id,
            Order.status == "paid",
            Order.paid_at.is_not(None),
        )
        .order_by(Order.paid_at.asc(), Order.id.asc())
        .limit(1)
    )
    if user.referral_locked_at is None and previous_paid_order is not None:
        user.referral_locked_at = previous_paid_order.paid_at or paid_at

    record = None
    if user.referral_code:
        record = db.scalar(
            select(ReferralCode).where(ReferralCode.code == user.referral_code)
        )

    if record is not None:
        order.referral_code_id = record.id
        order.referral_code_snapshot = record.code
        order.referral_label_snapshot = record.label
    else:
        order.referral_code_id = None
        order.referral_code_snapshot = None
        order.referral_label_snapshot = None

    order.referral_snapshot_at = paid_at
    if user.referral_locked_at is None:
        user.referral_locked_at = paid_at
    db.flush()


def get_referral_report(db: Session, actor: User) -> dict[str, object]:
    """Aggregate only paid orders that carry an explicit referral snapshot."""
    _require_manager(actor)
    rows = db.execute(
        select(
            Order.referral_code_snapshot,
            Order.referral_label_snapshot,
            Order.currency,
            func.count(Order.id),
            func.coalesce(func.sum(Order.amount_minor), 0),
            func.max(Order.paid_at),
        )
        .where(
            Order.status == "paid",
            Order.paid_at.is_not(None),
            Order.referral_snapshot_at.is_not(None),
        )
        .group_by(
            Order.referral_code_snapshot,
            Order.referral_label_snapshot,
            Order.currency,
        )
        .order_by(
            Order.referral_code_snapshot.asc().nullsfirst(),
            Order.currency.asc(),
        )
    ).all()

    referrals: list[dict[str, object]] = []
    currency_totals: dict[str, dict[str, int | str]] = {}
    paid_orders_total = 0
    for code, label, currency, count, gross, last_paid_at in rows:
        count_value = int(count or 0)
        gross_value = int(gross or 0)
        currency_value = str(currency or "")
        paid_orders_total += count_value
        totals = currency_totals.setdefault(
            currency_value,
            {"currency": currency_value, "paid_orders": 0, "gross_amount_minor": 0},
        )
        totals["paid_orders"] = int(totals["paid_orders"]) + count_value
        totals["gross_amount_minor"] = int(totals["gross_amount_minor"]) + gross_value
        referrals.append(
            {
                "code": code,
                "label": label or ("معرف مستقیم" if code is None else ""),
                "attribution": "direct" if code is None else "referral_code",
                "currency": currency_value,
                "paid_orders": count_value,
                "gross_amount_minor": gross_value,
                "last_paid_at": last_paid_at.isoformat() if last_paid_at else None,
            }
        )

    return {
        "source": "paid_order_referral_snapshots_v1",
        "snapshot_only": True,
        "paid_orders": paid_orders_total,
        "currency_totals": list(currency_totals.values()),
        "referrals": referrals,
    }
