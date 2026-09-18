"""Credit-based billing service for Dark Horse V2.

Rules:
- Free users receive exactly one non-expiring test credit.
- ``pack_3_tests`` adds exactly 3 credits after verified payment.
- Credit consumption is atomic at the database level.
- Payment verification is provider-agnostic; real ZarinPal and mock providers
  can implement the same interface in parallel.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from billing_models import Entitlement, Order, Payment, PaymentEvent, PremiumPlan, User

FREE_PLAN_CODE = "free_1_test"
PACK_3_TESTS_CODE = "pack_3_tests"
PACK_3_PRICE_RIAL = 2_490_000
PACK_3_CREDITS = 3
FREE_CREDITS = 1


class PaymentProvider(Protocol):
    name: str

    def request_payment(self, *, amount_rial: int, order_public_id: str, callback_url: str) -> dict: ...
    def verify_payment(self, *, amount_rial: int, authority: str) -> dict: ...


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_free_entitlement(db: Session, user_id: int) -> Entitlement:
    """Provision exactly one free credit once, idempotently."""
    free_plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == FREE_PLAN_CODE))
    if free_plan is None:
        raise ValueError("free plan is not configured")

    existing = db.scalar(
        select(Entitlement).where(
            Entitlement.user_id == user_id,
            Entitlement.plan_id == free_plan.id,
            Entitlement.source == "free",
        )
    )
    if existing is not None:
        return existing

    entitlement = Entitlement(
        user_id=user_id,
        plan_id=free_plan.id,
        source="free",
        credits_granted=FREE_CREDITS,
        credits_remaining=FREE_CREDITS,
        starts_at=utcnow(),
        expires_at=None,
        status="active",
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def create_pack_order(db: Session, user_id: int, plan_code: str = PACK_3_TESTS_CODE) -> Order:
    """Create an order using server-side plan pricing/credit values only."""
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("unknown user")
    plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == plan_code, PremiumPlan.is_active.is_(True)))
    if plan is None:
        raise ValueError("unknown or inactive plan")
    if plan_code != PACK_3_TESTS_CODE or plan.credits_granted != PACK_3_CREDITS:
        raise ValueError("unexpected credit-pack configuration")

    return Order(
        public_id=str(uuid4()),
        user_id=user_id,
        plan_id=plan.id,
        amount_minor=plan.price_minor,
        currency=plan.currency,
        status="pending",
    )


def initiate_payment(
    db: Session,
    user_id: int,
    provider: PaymentProvider,
    callback_url: str,
    plan_code: str = PACK_3_TESTS_CODE,
) -> tuple[Order, Payment, dict]:
    """Create pending order/payment and request provider authority."""
    order = create_pack_order(db, user_id, plan_code)
    db.add(order)
    db.flush()

    response = provider.request_payment(
        amount_rial=order.amount_minor,
        order_public_id=order.public_id,
        callback_url=callback_url,
    )
    authority = response.get("authority")
    if not authority:
        raise ValueError("payment provider did not return authority")

    payment = Payment(
        order_id=order.id,
        provider=provider.name,
        provider_request_id=str(response.get("request_id")) if response.get("request_id") is not None else None,
        provider_authority=str(authority),
        amount_minor=order.amount_minor,
        currency=order.currency,
        status="initiated",
    )
    db.add(payment)
    db.flush()
    return order, payment, response


def verify_and_grant(
    db: Session,
    payment_public_id: int,
    provider: PaymentProvider,
    authority: str,
    event_key: str,
    raw_callback: dict | None = None,
) -> Entitlement:
    """Verify payment and grant exactly plan.credits_granted in one transaction.

    A repeated callback for an already-verified payment is idempotent even when
    the gateway retries it with a different event key. The verified payment/order
    is the business idempotency boundary; ``event_key`` protects event insertion.
    """
    # Serialize concurrent gateway callbacks for the same payment before
    # checking status or creating an entitlement. Different callback event keys
    # must not be able to grant the same payment twice.
    payment = db.scalar(
        select(Payment).where(Payment.id == payment_public_id).with_for_update()
    )
    if payment is None:
        raise ValueError("unknown payment")
    order = db.get(Order, payment.order_id)
    if order is None:
        raise ValueError("payment order not found")
    plan = db.get(PremiumPlan, order.plan_id)
    user = db.get(User, order.user_id)
    if plan is None or user is None:
        raise ValueError("payment references missing plan/user")
    if authority != payment.provider_authority:
        raise ValueError("payment authority mismatch")

    existing_entitlement = db.scalar(select(Entitlement).where(Entitlement.order_id == order.id))
    if payment.status == "verified":
        if existing_entitlement is None:
            raise RuntimeError("verified payment exists without entitlement")
        return existing_entitlement

    existing_event = db.scalar(select(PaymentEvent).where(PaymentEvent.event_key == event_key))
    if existing_event is not None:
        if existing_entitlement is None:
            raise RuntimeError("idempotency event exists without entitlement")
        return existing_entitlement

    verification = provider.verify_payment(amount_rial=order.amount_minor, authority=authority)
    if not verification.get("verified"):
        payment.status = "failed"
        payment.raw_callback = raw_callback
        payment.verification_response = verification
        order.status = "failed"
        db.add(PaymentEvent(payment_id=payment.id, event_type="verification_failed", event_key=event_key, payload={"provider": provider.name}))
        raise ValueError("payment verification failed")

    if order.amount_minor != plan.price_minor:
        raise ValueError("order/plan amount mismatch")
    if plan.code != PACK_3_TESTS_CODE or plan.credits_granted != PACK_3_CREDITS:
        raise ValueError("unexpected credit-pack configuration")

    payment.status = "verified"
    payment.provider_transaction_id = str(verification.get("transaction_id")) if verification.get("transaction_id") else None
    payment.raw_callback = raw_callback
    payment.verification_response = verification
    payment.verified_at = utcnow()
    order.status = "paid"
    order.paid_at = utcnow()

    entitlement = Entitlement(
        user_id=user.id,
        plan_id=plan.id,
        source="payment",
        credits_granted=plan.credits_granted,
        credits_remaining=plan.credits_granted,
        starts_at=utcnow(),
        expires_at=None,
        status="active",
        order_id=order.id,
    )
    db.add(entitlement)
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            event_type="payment_verified_credits_granted",
            event_key=event_key,
            payload={"credits_granted": plan.credits_granted, "plan_code": plan.code},
        )
    )
    db.flush()
    return entitlement


def consume_one_test(db: Session, user_id: int) -> Entitlement:
    """Consume exactly one unexpired active test credit.

    PostgreSQL uses one atomic UPDATE ... RETURNING statement so the selected
    entitlement is decremented and returned in one database round-trip. The
    eligibility predicates remain on the UPDATE itself, preventing negative
    credits if another transaction changes the row while this statement waits.
    Other databases retain the existing ORM row-lock path.
    """
    now = utcnow()
    eligible = (
        Entitlement.user_id == user_id,
        Entitlement.status == "active",
        Entitlement.credits_remaining > 0,
        (Entitlement.expires_at.is_(None) | (Entitlement.expires_at > now)),
    )

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        candidate_id = (
            select(Entitlement.id)
            .where(*eligible)
            .order_by(Entitlement.created_at.asc(), Entitlement.id.asc())
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            update(Entitlement)
            .where(
                Entitlement.id == candidate_id,
                *eligible,
            )
            .values(credits_remaining=Entitlement.credits_remaining - 1)
            .returning(Entitlement)
        )
        entitlement = db.execute(stmt).scalar_one_or_none()
    else:
        stmt = (
            select(Entitlement)
            .where(*eligible)
            .order_by(Entitlement.created_at.asc(), Entitlement.id.asc())
        )
        entitlement = db.scalar(stmt)
        if entitlement is not None:
            entitlement.credits_remaining -= 1
            db.flush()

    if entitlement is None:
        raise ValueError("no valid test credits remaining")
    return entitlement
