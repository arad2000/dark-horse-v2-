"""Server-side OTP helper with mock and Kavenegar staging providers.

The challenge record is stored in PostgreSQL; only a derived code hash is
persisted. Real SMS delivery is enabled only when OTP_PROVIDER=kavenegar and
required staging credentials are present. Production does not receive a
provider-specific bypass.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import timedelta, timezone
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service import hash_password, normalize_phone, utcnow
from billing_models import RegistrationChallenge

OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
DEV_OTP_SECRET = "development-only-change-me"
KAVENEGAR_API_BASE = "https://api.kavenegar.com/v1"


def _otp_secret() -> str:
    secret = os.getenv("OTP_SECRET", "").strip()
    if secret:
        return secret
    provider = os.getenv("OTP_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return DEV_OTP_SECRET
    raise RuntimeError("OTP_SECRET must be configured for non-mock OTP providers")


def _hash_code(challenge_id: str, code: str) -> str:
    material = f"{challenge_id}:{code}:{_otp_secret()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _aware_utc(value):
    if value is None:
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def create_registration_challenge(db: Session, *, name: str, phone: str, password: str) -> tuple[RegistrationChallenge, str]:
    phone = normalize_phone(phone)
    clean_name = (name or "").strip()
    if len(clean_name) < 2:
        raise ValueError("name is required")
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("password must contain at least 8 characters")

    from billing_models import User
    if db.scalar(select(User).where(User.phone == phone)) is not None:
        raise ValueError("phone already registered")

    challenge_id = str(uuid4())
    code = f"{secrets.randbelow(1_000_000):06d}"
    row = RegistrationChallenge(
        challenge_id=challenge_id,
        name=clean_name,
        phone=phone,
        password_hash=hash_password(password),
        code_hash=_hash_code(challenge_id, code),
        attempts=0,
        max_attempts=OTP_MAX_ATTEMPTS,
        expires_at=utcnow() + timedelta(seconds=OTP_TTL_SECONDS),
    )
    db.add(row)
    db.flush()
    return row, code


def verify_registration_challenge(db: Session, *, challenge_id: str, code: str) -> RegistrationChallenge:
    row = db.scalar(select(RegistrationChallenge).where(RegistrationChallenge.challenge_id == challenge_id))
    if row is None:
        raise ValueError("unknown verification challenge")
    if row.consumed_at is not None:
        raise ValueError("verification challenge already used")
    expires_at = _aware_utc(row.expires_at)
    if expires_at <= utcnow():
        raise ValueError("verification code expired")
    if row.attempts >= row.max_attempts:
        raise ValueError("verification attempts exceeded")

    normalized = "".join(ch for ch in str(code or "") if ch.isdigit())
    if len(normalized) != 6 or not secrets.compare_digest(row.code_hash, _hash_code(row.challenge_id, normalized)):
        row.attempts += 1
        db.flush()
        raise ValueError("invalid verification code")

    row.consumed_at = utcnow()
    db.flush()
    return row


def _kavenegar_receptor(phone: str) -> str:
    normalized = normalize_phone(phone)
    return "+98" + normalized[1:]


def _kavenegar_config() -> tuple[str, str | None]:
    api_key = os.getenv("KAVENEGAR_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("KAVENEGAR_API_KEY is not configured")
    template = os.getenv("KAVENEGAR_OTP_TEMPLATE", "").strip() or None
    return api_key, template


def _raise_provider_error(response: httpx.Response) -> None:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    detail = None
    if isinstance(payload, dict):
        result = payload.get("return")
        if isinstance(result, dict):
            detail = result.get("message")
    raise RuntimeError(f"Kavenegar SMS failed ({response.status_code})" + (f": {detail}" if detail else ""))


def _send_kavenegar_sms(phone: str, code: str) -> None:
    api_key, template = _kavenegar_config()
    receptor = _kavenegar_receptor(phone)
    timeout = float(os.getenv("KAVENEGAR_TIMEOUT_SECONDS", "8"))

    if template:
        url = f"{KAVENEGAR_API_BASE}/{api_key}/verify/lookup.json"
        params = {"receptor": receptor, "token": code, "template": template}
    else:
        message = os.getenv("KAVENEGAR_OTP_MESSAGE", "کد تأیید اسب سیاه: {code}").format(code=code)
        sender = os.getenv("KAVENEGAR_SENDER", "").strip()
        if not sender:
            raise RuntimeError("KAVENEGAR_SENDER is required when KAVENEGAR_OTP_TEMPLATE is not configured")
        url = f"{KAVENEGAR_API_BASE}/{api_key}/sms/send.json"
        params = {"receptor": receptor, "message": message, "sender": sender}

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, params=params)
    except httpx.HTTPError as exc:
        raise RuntimeError("Kavenegar SMS request failed") from exc

    if response.status_code >= 400:
        _raise_provider_error(response)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Kavenegar returned an invalid response") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("return"), dict):
        raise RuntimeError("Kavenegar returned an unexpected response")
    status = payload["return"].get("status")
    if status not in {200, 201}:
        message = payload["return"].get("message")
        raise RuntimeError("Kavenegar rejected the SMS" + (f": {message}" if message else ""))


def send_code(phone: str, code: str) -> None:
    """Dispatch the OTP using mock or Kavenegar.

    ``OTP_EXPOSE_DEBUG_CODE`` is controlled by the API layer and remains
    staging/test-only; this function never returns or logs the OTP.
    """
    provider = os.getenv("OTP_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return
    if provider == "kavenegar":
        _send_kavenegar_sms(phone, code)
        return
    raise RuntimeError("unsupported OTP provider")
