"""Billing API service functions for staged/sandbox integration.

HTTP mounting lives in ``commercial_api.py``. This module remains the
API-facing orchestration for credit purchases while JSON scoring stays untouched.

Rules:
- Only ``pack_3_tests`` is purchasable here.
- Price/credit quantity always come from the DB plan.
- Mock and ZarinPal providers share the same provider contract.
- Callback verification is server-side and idempotent.
"""
from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from billing_credit_service import attach_order_id, initiate_payment, verify_and_grant
from billing_models import Order, Payment
from payment_providers import MockPaymentProvider, PaymentProvider, ZarinPalPaymentProvider


ALLOWED_PROVIDER_NAMES = {"mock", "zarinpal"}


def validate_callback_url(callback_url: str) -> str:
    parsed = urlparse(callback_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid callback URL")
    return callback_url


def build_provider(provider_name: str, *, zarinpal_merchant_id: str | None = None) -> PaymentProvider:
    if provider_name == "mock":
        return MockPaymentProvider()
    if provider_name == "zarinpal":
        return ZarinPalPaymentProvider(merchant_id=zarinpal_merchant_id)
    raise ValueError(f"unsupported payment provider: {provider_name}")


def create_payment_request(
    db: Session,
    *,
    user_id: int,
    callback_url: str,
    provider_name: str = "mock",
    zarinpal_merchant_id: str | None = None,
) -> dict:
    """Create a pending order/payment and return a provider redirect URL.

    The DB transaction is owned by the caller. The provider is called only after
    server-side plan resolution; the client cannot supply amount or credit count.
    The callback URL always includes the server-issued ``order_id``.
    """
    if provider_name not in ALLOWED_PROVIDER_NAMES:
        raise ValueError("unsupported payment provider")
    callback_url = validate_callback_url(callback_url)
    provider = build_provider(provider_name, zarinpal_merchant_id=zarinpal_merchant_id)
    order, payment, provider_response = initiate_payment(
        db,
        user_id,
        provider,
        callback_url,
        plan_code="pack_3_tests",
    )
    return {
        "order_id": order.public_id,
        "payment_id": payment.id,
        "provider": payment.provider,
        "amount_rial": payment.amount_minor,
        "currency": payment.currency,
        "payment_url": provider_response["payment_url"],
        "authority": payment.provider_authority,
        "callback_url": provider_response.get("callback_url") or attach_order_id(callback_url, order.public_id),
    }


def handle_payment_callback(
    db: Session,
    *,
    order_public_id: str,
    authority: str,
    status: str | None,
    provider_name: str,
    event_key: str,
    raw_callback: dict | None = None,
    zarinpal_merchant_id: str | None = None,
) -> dict:
    """Handle gateway callback and grant exactly three credits on success.

    ``Status != OK`` is treated as a failed/cancelled payment without calling
    provider verification. Repeated callbacks are idempotent.
    """
    if provider_name not in ALLOWED_PROVIDER_NAMES:
        raise ValueError("unsupported payment provider")
    if not order_public_id or not authority or not event_key:
        raise ValueError("callback identifiers are required")

    order = db.scalar(select(Order).where(Order.public_id == order_public_id))
    if order is None:
        raise ValueError("unknown order")
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == order.id,
            Payment.provider == provider_name,
            Payment.provider_authority == authority,
        )
    )
    if payment is None:
        raise ValueError("unknown payment authority")

    # Gateway callbacks commonly include Status=OK. Never verify cancelled/failed
    # callbacks, and never let a client claim a successful payment by inventing it.
    if (status or "").upper() != "OK":
        payment.status = "failed"
        order.status = "failed"
        payment.raw_callback = raw_callback
        return {
            "verified": False,
            "status": "failed",
            "order_id": order.public_id,
            "credits_added": 0,
        }

    provider = build_provider(provider_name, zarinpal_merchant_id=zarinpal_merchant_id)
    entitlement = verify_and_grant(
        db,
        payment.id,
        provider,
        authority,
        event_key,
        raw_callback=raw_callback,
    )
    return {
        "verified": True,
        "status": "paid",
        "order_id": order.public_id,
        "credits_added": entitlement.credits_granted,
        "credits_remaining": entitlement.credits_remaining,
    }
