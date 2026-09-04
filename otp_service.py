"""Small server-side OTP helper for registration verification.

The challenge record is stored in PostgreSQL; only a derived code hash is
persisted. The default provider is a no-op mock suitable for CI/staging. A real
SMS provider can be added behind the same send_code contract before production.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service import hash_password, normalize_phone, utcnow
from billing_models import RegistrationChallenge

OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
DEV_OTP_SECRET = "development-only-change-me"


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
    if row.expires_at <= utcnow():
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


def send_code(phone: str, code: str) -> None:
    """Dispatch the OTP.

    ``mock`` intentionally does not expose the code to the API response. The
    code is available to test fixtures by creating the challenge directly.
    """
    provider = os.getenv("OTP_PROVIDER", "mock").strip().lower()
    if provider not in {"mock", "sms"}:
        raise RuntimeError("unsupported OTP provider")
    if provider == "mock":
        return
    raise RuntimeError("OTP SMS provider is not configured")
