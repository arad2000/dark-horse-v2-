"""Production billing configuration guard.

The commercial provider remains fail-closed in production until the merchant
is activated. During the controlled launch window, authentication and the
single free test are allowed through ``BILLING_FREE_ONLY_MODE=true`` while all
commercial payment creation is disabled.
"""
from __future__ import annotations

import os

from fastapi import HTTPException


def _is_true(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def is_production_free_only_mode() -> bool:
    environment = os.getenv("APP_ENV", "").strip().lower()
    return environment in {"production", "prod"} and _is_true("BILLING_FREE_ONLY_MODE")


def assert_production_billing_configuration() -> None:
    """Reject unsafe billing configuration while allowing the approved free-only launch."""
    environment = os.getenv("APP_ENV", "").strip().lower()
    if environment not in {"production", "prod"}:
        return

    if is_production_free_only_mode():
        if _is_true("BILLING_FREE_MODE"):
            raise HTTPException(
                status_code=503,
                detail="BILLING_FREE_MODE cannot be combined with production free-only launch",
            )
        return

    if _is_true("BILLING_SANDBOX_MODE"):
        if not _is_true("BILLING_SANDBOX_APPROVED"):
            raise HTTPException(status_code=503, detail="sandbox billing requires explicit approval")
        provider = os.getenv("BILLING_PROVIDER", "").strip().lower()
        if provider not in {"mock", "zarinpal"}:
            raise HTTPException(status_code=503, detail="sandbox billing requires mock or zarinpal provider")
        if provider == "zarinpal":
            if not _is_true("ZARINPAL_SANDBOX"):
                raise HTTPException(status_code=503, detail="sandbox billing requires ZARINPAL_SANDBOX=true")
            if not os.getenv("ZARINPAL_MERCHANT_ID", "").strip():
                raise HTTPException(status_code=503, detail="sandbox billing requires ZARINPAL_MERCHANT_ID")
        return

    if _is_true("BILLING_FREE_MODE"):
        raise HTTPException(
            status_code=503,
            detail="production billing cannot run with BILLING_FREE_MODE enabled",
        )

    provider = os.getenv("BILLING_PROVIDER", "").strip().lower()
    if provider != "zarinpal":
        raise HTTPException(
            status_code=503,
            detail="production billing requires BILLING_PROVIDER=zarinpal",
        )

    merchant_id = os.getenv("ZARINPAL_MERCHANT_ID", "").strip()
    if not merchant_id:
        raise HTTPException(
            status_code=503,
            detail="production billing requires ZARINPAL_MERCHANT_ID",
        )

    if _is_true("ZARINPAL_SANDBOX"):
        raise HTTPException(
            status_code=503,
            detail="production billing cannot use the ZarinPal sandbox",
        )

    if not _is_true("ZARINPAL_PRODUCTION_APPROVED"):
        raise HTTPException(
            status_code=503,
            detail="live ZarinPal requires explicit production approval",
        )
