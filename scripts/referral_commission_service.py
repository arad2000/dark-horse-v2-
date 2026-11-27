"""Referral code ownership and commission accrual.

Deliberately narrow: this module records who owns a code and what each paid
order owes that person. It never moves money, never touches the credit ledger,
and never alters an order's amount. Settlement is a status flag an operator
sets after paying out of band.
"""
from __future__ import annotations

import re
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from billing_models import (
    Order,
    ReferralCode,
    ReferralCommission,
    ReferralMarketer,
    ReferralSignup,
    User,
)

CODE_PATTERN = re.compile(r"^[A-Z0-9]{4,32}$")
ALPHABET = string.ascii_uppercase + string.digits
BASIS_POINTS = 10_000


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_manager(actor: User) -> None:
    if actor is None or actor.role != "admin":
        raise PermissionError("manager access required")


def normalize_code(value: str | None) -> str:
    candidate = (value or "").strip().upper()
    if not CODE_PATTERN.fullmatch(candidate):
        raise ValueError("code must contain 4 to 32 ASCII letters or digits")
    return candidate


def register_marketer(
    db: Session,
    actor: User,
    *,
    name: str,
    phone: str | None = None,
    user_id: int | None = None,
    commission_bps: int = 0,
    note: str | None = None,
) -> ReferralMarketer:
    """Create the commission earner. Link to an account when they have one."""
    _require_manager(actor)
    clean_name = (name or "").strip()
    if not clean_name or len(clean_name) > 200:
        raise ValueError("name must contain 1 to 200 characters")
    if not (0 <= int(commission_bps) <= BASIS_POINTS):
        raise ValueError("commission_bps must be between 0 and 10000")
    if user_id is not None and db.get(User, int(user_id)) is None:
        raise ValueError("linked user does not exist")

    marketer = ReferralMarketer(
        public_id="mk-" + secrets.token_hex(8),
        user_id=int(user_id) if user_id is not None else None,
        name=clean_name,
        phone=(phone or "").strip() or None,
        commission_bps=int(commission_bps),
        note=(note or "").strip() or None,
        is_active=True,
    )
    db.add(marketer)
    db.flush()
    return marketer


def create_code_for_marketer(
    db: Session,
    actor: User,
    *,
    marketer_id: int,
    code: str | None = None,
) -> ReferralCode:
    _require_manager(actor)
    marketer = db.get(ReferralMarketer, int(marketer_id))
    if marketer is None:
        raise ValueError("marketer does not exist")
    if not marketer.is_active:
        raise ValueError("marketer is inactive")

    if code and code.strip():
        normalized = normalize_code(code)
    else:
        normalized = ""
        for _ in range(10):
            candidate = "".join(secrets.choice(ALPHABET) for _ in range(8))
            if db.scalar(select(ReferralCode.id).where(ReferralCode.code == candidate)) is None:
                normalized = candidate
                break
        if not normalized:
            raise RuntimeError("could not allocate a unique referral code")

    if db.scalar(select(ReferralCode.id).where(ReferralCode.code == normalized)) is not None:
        raise ValueError("referral code already exists")

    row = ReferralCode(code=normalized, marketer_id=marketer.id, is_active=True)
    db.add(row)
    db.flush()
    return row


def resolve_owner(db: Session, code: str | None) -> tuple[ReferralCode, ReferralMarketer] | None:
    """Return the active code + owner, or None. Never raises for a bad code."""
    if not code:
        return None
    normalized = (code or "").strip().upper()
    if not CODE_PATTERN.fullmatch(normalized):
        return None
    row = db.scalar(select(ReferralCode).where(ReferralCode.code == normalized, ReferralCode.is_active.is_(True)))
    if row is None:
        return None
    marketer = db.get(ReferralMarketer, row.marketer_id)
    if marketer is None or not marketer.is_active:
        return None
    return row, marketer


def snapshot_order_owner(db: Session, order: Order, code: str | None) -> None:
    """Freeze the owner and rate onto the order so later edits cannot move money."""
    resolved = resolve_owner(db, code)
    if resolved is None:
        order.marketer_id_snapshot = None
        order.commission_bps_snapshot = None
        return
    _row, marketer = resolved
    order.marketer_id_snapshot = int(marketer.id)
    order.commission_bps_snapshot = int(marketer.commission_bps)


def accrue_commission(db: Session, order: Order) -> ReferralCommission | None:
    """Create the commission row for one paid order. Idempotent by order id.

    Integer math only, truncated down: ``gross * bps // 10000``. A zero-rate
    owner produces no row at all rather than a meaningless zero record.
    """
    if order.marketer_id_snapshot is None:
        return None
    existing = db.scalar(select(ReferralCommission).where(ReferralCommission.order_id == order.id))
    if existing is not None:
        return existing

    bps = int(order.commission_bps_snapshot or 0)
    gross = int(order.amount_minor or 0)
    amount = gross * bps // BASIS_POINTS
    if bps <= 0 or amount <= 0:
        return None

    row = ReferralCommission(
        order_id=int(order.id),
        marketer_id=int(order.marketer_id_snapshot),
        referral_code=str(order.referral_code_snapshot or ""),
        gross_amount_minor=gross,
        commission_bps=bps,
        commission_amount_minor=amount,
        currency=str(order.currency or ""),
        status="accrued",
    )
    db.add(row)
    db.flush()
    return row


def settle_commission(db: Session, actor: User, *, commission_id: int, note: str | None = None) -> ReferralCommission:
    """Mark one accrual as paid. Records intent only; no money moves here."""
    _require_manager(actor)
    row = db.get(ReferralCommission, int(commission_id))
    if row is None:
        raise ValueError("commission does not exist")
    if row.status == "settled":
        return row
    row.status = "settled"
    row.settled_at = utcnow()
    if note:
        row.note = (note or "").strip()[:500]
    db.flush()
    return row


def marketer_statement(db: Session, actor: User, *, marketer_id: int | None = None) -> dict[str, object]:
    """Who is owed what, per marketer and per currency."""
    _require_manager(actor)
    stmt = (
        select(
            ReferralCommission.marketer_id,
            ReferralMarketer.name,
            ReferralMarketer.phone,
            ReferralCommission.currency,
            ReferralCommission.status,
            func.count(ReferralCommission.id),
            func.coalesce(func.sum(ReferralCommission.commission_amount_minor), 0),
            func.coalesce(func.sum(ReferralCommission.gross_amount_minor), 0),
        )
        .join(ReferralMarketer, ReferralMarketer.id == ReferralCommission.marketer_id)
        .group_by(
            ReferralCommission.marketer_id,
            ReferralMarketer.name,
            ReferralMarketer.phone,
            ReferralCommission.currency,
            ReferralCommission.status,
        )
        .order_by(ReferralCommission.marketer_id.asc(), ReferralCommission.currency.asc())
    )
    if marketer_id is not None:
        stmt = stmt.where(ReferralCommission.marketer_id == int(marketer_id))

    people: dict[int, dict[str, object]] = {}
    for mk_id, name, phone, currency, status, count, commission, gross in db.execute(stmt).all():
        person = people.setdefault(
            int(mk_id),
            {"marketer_id": int(mk_id), "name": name, "phone": phone, "currencies": {}},
        )
        bucket = person["currencies"].setdefault(
            str(currency or ""),
            {"currency": str(currency or ""), "orders": 0, "gross_amount_minor": 0,
             "accrued_amount_minor": 0, "settled_amount_minor": 0},
        )
        bucket["orders"] += int(count or 0)
        bucket["gross_amount_minor"] += int(gross or 0)
        if status == "settled":
            bucket["settled_amount_minor"] += int(commission or 0)
        else:
            bucket["accrued_amount_minor"] += int(commission or 0)

    for person in people.values():
        person["currencies"] = list(person["currencies"].values())
    return {"marketers": list(people.values())}


def marketer_recruitment_report(db: Session, actor: User) -> dict[str, object]:
    """How many people each marketer brought, and what that turned into.

    Deliberately separates the two questions an operator actually asks:
      * ``signups``   — people who registered with the code (no purchase needed)
      * ``confirmed`` — those signups who later bought something
      * ``commission`` — money owed, from paid orders only

    A signup that never buys still counts toward ``signups``; that is the whole
    point of recording attribution at registration.
    """
    _require_manager(actor)

    # head-count per marketer, straight from the signup ledger
    signup_rows = db.execute(
        select(
            ReferralMarketer.id,
            ReferralMarketer.name,
            ReferralMarketer.phone,
            ReferralMarketer.user_id,
            ReferralMarketer.commission_bps,
            ReferralMarketer.is_active,
            ReferralMarketer.self_service,
            func.count(ReferralSignup.id),
            func.max(ReferralSignup.created_at),
        )
        .outerjoin(ReferralSignup, ReferralSignup.marketer_id == ReferralMarketer.id)
        .group_by(
            ReferralMarketer.id,
            ReferralMarketer.name,
            ReferralMarketer.phone,
            ReferralMarketer.user_id,
            ReferralMarketer.commission_bps,
            ReferralMarketer.is_active,
            ReferralMarketer.self_service,
        )
        .order_by(ReferralMarketer.id.asc())
    ).all()

    # buyers: signups that also produced at least one paid, attributed order
    confirmed_rows = db.execute(
        select(
            ReferralSignup.marketer_id,
            func.count(func.distinct(ReferralSignup.user_id)),
        )
        .join(Order, Order.user_id == ReferralSignup.user_id)
        .where(
            Order.status == "paid",
            Order.paid_at.is_not(None),
            Order.marketer_id_snapshot == ReferralSignup.marketer_id,
        )
        .group_by(ReferralSignup.marketer_id)
    ).all()
    confirmed = {int(mid): int(n) for mid, n in confirmed_rows}

    # money owed, from the immutable commission ledger
    money_rows = db.execute(
        select(
            ReferralCommission.marketer_id,
            ReferralCommission.currency,
            ReferralCommission.status,
            func.count(ReferralCommission.id),
            func.coalesce(func.sum(ReferralCommission.commission_amount_minor), 0),
        )
        .group_by(ReferralCommission.marketer_id, ReferralCommission.currency, ReferralCommission.status)
    ).all()
    money: dict[int, dict[str, dict[str, int]]] = {}
    for mid, currency, status, count, amount in money_rows:
        bucket = money.setdefault(int(mid), {}).setdefault(
            str(currency or ""),
            {"orders": 0, "accrued_amount_minor": 0, "settled_amount_minor": 0},
        )
        bucket["orders"] += int(count or 0)
        if status == "settled":
            bucket["settled_amount_minor"] += int(amount or 0)
        else:
            bucket["accrued_amount_minor"] += int(amount or 0)

    marketers: list[dict[str, object]] = []
    for mk_id, name, phone, user_id, bps, active, self_service, signups, last_signup in signup_rows:
        mk_id = int(mk_id)
        marketers.append(
            {
                "marketer_id": mk_id,
                "name": name,
                "phone": phone,
                "linked_user_id": int(user_id) if user_id else None,
                "commission_bps": int(bps or 0),
                "commission_percent": round(int(bps or 0) / 100, 2),
                "is_active": bool(active),
                "self_service": bool(self_service),
                "signups": int(signups or 0),
                "confirmed_buyers": confirmed.get(mk_id, 0),
                "last_signup_at": last_signup.isoformat() if last_signup else None,
                "currencies": [
                    {"currency": cur, **vals}
                    for cur, vals in sorted(money.get(mk_id, {}).items())
                ],
            }
        )

    return {
        "totals": {
            "marketers": len(marketers),
            "signups": sum(m["signups"] for m in marketers),
            "confirmed_buyers": sum(m["confirmed_buyers"] for m in marketers),
        },
        "marketers": marketers,
    }


def signups_of_marketer(db: Session, actor: User, *, marketer_id: int) -> dict[str, object]:
    """The actual list of people a marketer brought, with their purchase state."""
    _require_manager(actor)
    rows = db.execute(
        select(
            User.id,
            User.name,
            User.phone,
            User.status,
            ReferralSignup.code,
            ReferralSignup.created_at,
            func.count(Order.id),
        )
        .join(User, User.id == ReferralSignup.user_id)
        .outerjoin(
            Order,
            (Order.user_id == ReferralSignup.user_id)
            & (Order.status == "paid")
            & (Order.paid_at.is_not(None))
            & (Order.marketer_id_snapshot == ReferralSignup.marketer_id),
        )
        .where(ReferralSignup.marketer_id == int(marketer_id))
        .group_by(
            User.id,
            User.name,
            User.phone,
            User.status,
            ReferralSignup.code,
            ReferralSignup.created_at,
        )
        .order_by(ReferralSignup.created_at.desc())
    ).all()
    return {
        "marketer_id": int(marketer_id),
        "count": len(rows),
        "people": [
            {
                "user_id": int(uid),
                "name": name,
                "phone": phone,
                "status": status,
                "code": code,
                "joined_at": created.isoformat() if created else None,
                "paid_orders": int(paid or 0),
                "confirmed": int(paid or 0) > 0,
            }
            for uid, name, phone, status, code, created, paid in rows
        ],
    }


def my_referral_code(db: Session, user: User) -> dict[str, object]:
    """The caller's own shareable code, created on first call.

    Any signed-in user can hold one. Idempotent: calling twice returns the same
    code, and the partial unique index prevents a second self-service row.
    A self-service owner starts at 0 bps, so minting a code never creates a
    payout obligation by itself; an admin sets the real rate for partners.
    """
    existing = db.scalar(
        select(ReferralMarketer).where(
            ReferralMarketer.user_id == int(user.id),
            ReferralMarketer.self_service.is_(True),
        )
    )
    if existing is not None:
        code_row = db.scalar(
            select(ReferralCode)
            .where(ReferralCode.marketer_id == existing.id, ReferralCode.is_active.is_(True))
            .order_by(ReferralCode.id.asc())
        )
        if code_row is None:
            code_row = _mint_personal_code(db, existing, user)
        return _my_code_payload(db, existing, code_row)

    marketer = ReferralMarketer(
        public_id="mk-" + secrets.token_hex(8),
        user_id=int(user.id),
        name=(user.name or "کاربر")[:200],
        phone=user.phone,
        commission_bps=0,
        is_active=True,
        self_service=True,
    )
    db.add(marketer)
    db.flush()
    code_row = _mint_personal_code(db, marketer, user)
    return _my_code_payload(db, marketer, code_row)


def _mint_personal_code(db: Session, marketer: ReferralMarketer, user: User) -> ReferralCode:
    for _ in range(10):
        candidate = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if db.scalar(select(ReferralCode.id).where(ReferralCode.code == candidate)) is None:
            row = ReferralCode(
                code=candidate,
                marketer_id=int(marketer.id),
                is_active=True,
                created_by_user_id=int(user.id),
            )
            db.add(row)
            db.flush()
            return row
    raise RuntimeError("could not allocate a unique referral code")


def _my_code_payload(db: Session, marketer: ReferralMarketer, code_row: ReferralCode) -> dict[str, object]:
    signups = db.scalar(
        select(func.count(ReferralSignup.id)).where(ReferralSignup.marketer_id == marketer.id)
    ) or 0
    return {
        "code": code_row.code,
        "marketer_id": int(marketer.id),
        "commission_bps": int(marketer.commission_bps),
        "is_active": bool(code_row.is_active),
        "signups": int(signups),
        "share_text": (
            "با کد معرف من ثبت‌نام کن: " + code_row.code
        ),
    }
