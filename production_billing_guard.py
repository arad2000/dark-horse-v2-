"""Production billing configuration guard.

Production normally requires approved live ZarinPal. A separately approved,
explicit sandbox mode may be enabled temporarily for payment rehearsal.
"""
from __future__ import annotations

import os

from fastapi import HTTPException


def _is_true(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def assert_production_billing_configuration() -> None:
    """Fail closed in production unless live billing or explicit sandbox mode is configured."""
    environment = os.getenv("APP_ENV", "").strip().lower()
    if environment not in {"production", "prod"}:
        return

    sandbox_mode = _is_true("BILLING_SANDBOX_MODE")
    if sandbox_mode:
        if not _is_true("BILLING_SANDBOX_APPROVED"):
            raise HTTPException(status_code=503, detail="sandbox billing requires explicit approval")
        provider = os.getenv("BILLING_PROVIDER", "").strip().lower()
        if provider not in {"mock", "zarinpal"}:
            raise HTTPException(status_code=503, detail="sandbox billing requires mock or zarinpal provider")
        if provider == "zarinpal" and not _is_true("ZARINPAL_SANDBOX"):
            raise HTTPException(status_code=503, detail="sandbox billing requires ZARINPAL_SANDBOX=true")
        if provider == "zarinpal" and not os.getenv("ZARINPAL_MERCHANT_ID", "").strip():
            raise HTTPException(status_code=503, detail="sandbox billing requires ZARINPAL_MERCHANT_ID")
        return

    if _is_true("BILLING_FREE_MODE"):
        raise HTTPException(status_code=503, detail="production billing cannot run with BILLING_FREE_MODE enabled")

    provider = os.getenv("BILLING_PROVIDER", "").strip().lower()
    if provider != "zarinpal":
        raise HTTPException(status_code=503, detail="production billing requires BILLING_PROVIDER=zarinpal")

    merchant_id = os.getenv("ZARINPAL_MERCHANT_ID", "").strip()
    if not merchant_id:
        raise HTTPException(status_code=503, detail="production billing requires ZARINPAL_MERCHANT_ID")

    if _is_true("ZARINPAL_SANDBOX"):
        raise HTTPException(status_code=503, detail="production billing cannot use the ZarinPal sandbox")

    if not _is_true("ZARINPAL_PRODUCTION_APPROVED"):
        raise HTTPException(status_code=503, detail="live ZarinPal requires explicit production approval")
