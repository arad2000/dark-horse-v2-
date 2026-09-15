"""Server-side phone verification using Kavenegar VerifyLookup.

OTP values are never persisted in plaintext. Registration data is held only in a
short-lived verification challenge until the phone number is verified.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service import hash_password
from billing_models import PhoneVerification, User

OTP_TTL_SECONDS = 300
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5
OTP_LENGTH = 6


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_phone(phone: str) -> str:
    value = "".join((phone or "").split())
    value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not value:
        raise ValueError("phone is required")
    if not value.startswith("09") or len(value) != 11 or not value.isdigit():
        raise ValueError("invalid Iranian mobile number")
    return value


def _hash_code(challenge_id: str, code: str) -> str:
    pepper = os.getenv("OTP_HASH_PEPPER", "")
    return hashlib.sha256(f"{pepper}:{challenge_id}:{code}".encode("utf-8")).hexdigest()


def _otp_client() -> tuple[str, str]:
    api_key = os.getenv("KAVENEGAR_API_KEY", "").strip()
    template = os.getenv("KAVENEGAR_OTP_TEMPLATE", "registerverify").strip()
    if not api_key:
        raise RuntimeError("KAVENEGAR_API_KEY is not configured")
    if not template:
        raise RuntimeError("KAVENEGAR_OTP_TEMPLATE is not configured")
    return api_key, template


def _send_kavenegar_otp(phone: str, code: str) -> None:
    api_key, template = _otp_client()
    url = f"https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"
    payload = {
        "receptor": phone,
        "token": code,
        "template": template,
        "type": "sms",
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, data=payload)
        response.raise_for_status()
        body = response.json()
    result = body.get("return") or {}
    if str(result.get("status")) != "200":
        raise RuntimeError(result.get("message") or "Kavenegar rejected the OTP request")


def request_registration_otp(db: Session, *, name: str, phone: str, password: str) -> dict[str, object]:
    phone = normalize_phone(phone)
    name = (name or "").strip()
    if len(name) < 2:
        raise ValueError("name is required")
    if len(password or "") < 8:
        raise ValueError("password must contain at least 8 characters")
    if db.scalar(select(User).where(User.phone == phone)) is not None:
        raise ValueError("phone already registered")

    now = utcnow()
    recent = db.scalar(
        select(PhoneVerification)
        .where(PhoneVerification.phone == phone, PhoneVerification.purpose == "register")
        .order_by(PhoneVerification.created_at.desc())
    )
    if recent and recent.created_at:
        created = recent.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if now - created < timedelta(seconds=RESEND_COOLDOWN_SECONDS):
            raise TimeoutError("please wait before requesting another code")

    challenge_id = secrets.token_urlsafe(18)
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = PhoneVerification(
        challenge_id=challenge_id,
        phone=phone,
        purpose="register",
        name=name,
        password_hash=hash_password(password),
        code_hash=_hash_code(challenge_id, code),
        expires_at=now + timedelta(seconds=OTP_TTL_SECONDS),
        attempts=0,
    )
    db.add(challenge)
    db.flush()
    try:
        _send_kavenegar_otp(phone, code)
    except Exception:
        db.delete(challenge)
        db.flush()
        raise
    return {
        "otp_required": True,
        "challenge_id": challenge_id,
        "expires_in": OTP_TTL_SECONDS,
        "resend_after": RESEND_COOLDOWN_SECONDS,
    }


def verify_registration_otp(db: Session, *, challenge_id: str, code: str) -> tuple[User, str]:
    code = (code or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not challenge_id or not code.isdigit() or len(code) != OTP_LENGTH:
        raise ValueError("invalid verification code")

    challenge = db.scalar(
        select(PhoneVerification).where(
            PhoneVerification.challenge_id == challenge_id,
            PhoneVerification.purpose == "register",
        )
    )
    if challenge is None:
        raise ValueError("verification request not found")
    if challenge.verified_at is not None:
        raise ValueError("verification request already used")
    expires = challenge.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= utcnow():
        raise TimeoutError("verification code expired")
    if int(challenge.attempts or 0) >= MAX_ATTEMPTS:
        raise PermissionError("too many verification attempts")

    challenge.attempts = int(challenge.attempts or 0) + 1
    expected = _hash_code(challenge_id, code)
    if not secrets.compare_digest(expected, challenge.code_hash):
        db.flush()
        raise ValueError("incorrect verification code")

    if db.scalar(select(User).where(User.phone == challenge.phone)) is not None:
        raise ValueError("phone already registered")

    user = User(
        public_id=secrets.token_hex(18),
        name=challenge.name,
        phone=challenge.phone,
        password_hash=challenge.password_hash,
    )
    db.add(user)
    db.flush()
    from auth_service import issue_session
    token, _ = issue_session(db, user)
    challenge.verified_at = utcnow()
    db.flush()
    return user, token
