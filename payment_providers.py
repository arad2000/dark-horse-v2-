"""Payment provider contracts and parallel Mock/ZarinPal implementations.

The real ZarinPal adapter is intentionally developed in parallel with the Mock
provider. The Mock provider is used for deterministic CI; production credentials
are never required for tests. Both implement the same request/verify contract.

Sandbox mode uses sandbox.zarinpal.com. Live mode is only reachable when the
caller constructs the provider with sandbox=False (commercial_api additionally
requires ZARINPAL_PRODUCTION_APPROVED).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass(frozen=True)
class ProviderResponse:
    verified: bool = False
    authority: str | None = None
    transaction_id: str | None = None
    request_id: str | None = None
    code: int | None = None
    message: str | None = None
    raw: dict[str, Any] | None = None


class PaymentProvider(Protocol):
    name: str

    def request_payment(self, *, amount_rial: int, order_public_id: str, callback_url: str) -> dict[str, Any]:
        ...

    def verify_payment(self, *, amount_rial: int, authority: str) -> dict[str, Any]:
        ...


class MockPaymentProvider:
    name = "mock"

    def __init__(self, authority: str = "MOCK-AUTH-001", transaction_id: str = "MOCK-REF-001") -> None:
        self.authority = authority
        self.transaction_id = transaction_id

    def request_payment(self, *, amount_rial: int, order_public_id: str, callback_url: str) -> dict[str, Any]:
        return {
            "code": 100,
            "authority": self.authority,
            "request_id": f"mock-request:{order_public_id}",
            "payment_url": f"https://sandbox.example.invalid/pay/{self.authority}",
            "amount_rial": amount_rial,
            "callback_url": callback_url,
        }

    def verify_payment(self, *, amount_rial: int, authority: str) -> dict[str, Any]:
        if authority != self.authority:
            return {"verified": False, "code": -1, "message": "mock authority mismatch"}
        return {
            "verified": True,
            "code": 100,
            "transaction_id": self.transaction_id,
            "amount_rial": amount_rial,
        }


class ZarinPalPaymentProvider:
    """Real ZarinPal REST v4 adapter.

    It is safe to instantiate without credentials in CI because network calls occur
    only when request_payment/verify_payment are explicitly invoked.
    """

    name = "zarinpal"
    LIVE_BASE_URL = "https://api.zarinpal.com/pg/v4/payment"
    SANDBOX_BASE_URL = "https://sandbox.zarinpal.com/pg/v4/payment"
    LIVE_STARTPAY_URL = "https://www.zarinpal.com/pg/StartPay"
    SANDBOX_STARTPAY_URL = "https://sandbox.zarinpal.com/pg/StartPay"
    DEFAULT_BASE_URL = LIVE_BASE_URL

    def __init__(
        self,
        merchant_id: str | None = None,
        base_url: str | None = None,
        timeout: float = 15.0,
        sandbox: bool | None = None,
    ):
        self.merchant_id = merchant_id or os.getenv("ZARINPAL_MERCHANT_ID", "")
        if sandbox is None:
            sandbox = os.getenv("ZARINPAL_SANDBOX", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.sandbox = bool(sandbox)
        default_base = self.SANDBOX_BASE_URL if self.sandbox else self.LIVE_BASE_URL
        self.base_url = (base_url or os.getenv("ZARINPAL_BASE_URL") or default_base).rstrip("/")
        self.timeout = timeout

    def _require_credentials(self) -> None:
        if not self.merchant_id:
            raise RuntimeError("ZARINPAL_MERCHANT_ID is not configured")

    def _startpay_url(self, authority: str) -> str:
        base = self.SANDBOX_STARTPAY_URL if self.sandbox else self.LIVE_STARTPAY_URL
        return f"{base}/{authority}"

    def request_payment(self, *, amount_rial: int, order_public_id: str, callback_url: str) -> dict[str, Any]:
        self._require_credentials()
        payload = {
            "merchant_id": self.merchant_id,
            "amount": int(amount_rial),
            "callback_url": callback_url,
            "description": f"Dark Horse — {order_public_id}",
            "metadata": {"order_public_id": order_public_id},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/request.json", json=payload)
            response.raise_for_status()
            body = response.json()

        data = body.get("data") or {}
        errors = body.get("errors") or {}
        code = data.get("code")
        if code != 100:
            raise RuntimeError(f"ZarinPal payment request failed: code={code}, errors={errors}")
        authority = data.get("authority")
        if not authority:
            raise RuntimeError("ZarinPal payment request did not return authority")
        return {
            "code": code,
            "authority": authority,
            "request_id": data.get("request_id"),
            "payment_url": self._startpay_url(str(authority)),
            "callback_url": callback_url,
            "raw": body,
        }

    def verify_payment(self, *, amount_rial: int, authority: str) -> dict[str, Any]:
        self._require_credentials()
        payload = {
            "merchant_id": self.merchant_id,
            "amount": int(amount_rial),
            "authority": authority,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/verify.json", json=payload)
            response.raise_for_status()
            body = response.json()

        data = body.get("data") or {}
        errors = body.get("errors") or {}
        code = data.get("code")
        verified = code in (100, 101)
        return {
            "verified": verified,
            "code": code,
            "transaction_id": str(data.get("ref_id")) if data.get("ref_id") is not None else None,
            "message": errors.get("message") if errors else None,
            "raw": body,
        }
