"""Phone-OTP password reset service for Dark Horse V2.

OTP values are never stored in plaintext. Reset challenges are short-lived,
rate-limited, limited to a small number of attempts, and single-use.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service import hash_password, issue_session, revoke_all_sessions
from billing_models import PhoneVerification, User
from phone_verification_service import enforce_sms_rate_limit
from database import get_db

OTP_TTL_SECONDS = 300
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5
OTP_LENGTH = 6
RESET_PURPOSE = "password_reset"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_phone(phone: str) -> str:
    value = "".join((phone or "").split())
    value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not value or not value.startswith("09") or len(value) != 11 or not value.isdigit():
        raise ValueError("invalid Iranian mobile number")
    return value


def _hash_code(challenge_id: str, code: str) -> str:
    pepper = os.getenv("OTP_HASH_PEPPER", "")
    return hashlib.sha256(f"{pepper}:{challenge_id}:{code}".encode("utf-8")).hexdigest()


def _send_reset_otp(phone: str, code: str) -> None:
    api_key = os.getenv("KAVENEGAR_API_KEY", "").strip()
    template = os.getenv("KAVENEGAR_RESET_OTP_TEMPLATE", "passwordreset").strip()
    if not api_key:
        raise RuntimeError("KAVENEGAR_API_KEY is not configured")
    if not template:
        raise RuntimeError("KAVENEGAR_RESET_OTP_TEMPLATE is not configured")
    url = f"https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"
    payload = {"receptor": phone, "token": code, "template": template, "type": "sms"}
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, data=payload)
        response.raise_for_status()
        body = response.json()
    result = body.get("return") or {}
    if str(result.get("status")) != "200":
        raise RuntimeError(result.get("message") or "Kavenegar rejected the password reset OTP request")


def request_password_reset_otp(
    db: Session, *, phone: str, request_ip: str | None = None
) -> dict[str, object]:
    """Issue a reset challenge when the phone is registered.

    The API keeps a generic response for unknown phones to avoid account
    enumeration. Only the presence of a challenge_id allows the next step.
    """
    phone = normalize_phone(phone)
    user = db.scalar(select(User).where(User.phone == phone, User.status == "active"))
    if user is None or not user.password_hash:
        return {"otp_required": False, "message": "اگر حسابی با این شماره وجود داشته باشد، کد بازیابی ارسال می‌شود."}

    now = utcnow()
    enforce_sms_rate_limit(db, phone=phone, request_ip=request_ip)
    recent = db.scalar(
        select(PhoneVerification)
        .where(PhoneVerification.phone == phone, PhoneVerification.purpose == RESET_PURPOSE)
        .order_by(PhoneVerification.created_at.desc())
    )
    created = _as_utc(recent.created_at) if recent else None
    if created is not None and now - created < timedelta(seconds=RESEND_COOLDOWN_SECONDS):
        raise TimeoutError("please wait before requesting another code")

    challenge_id = secrets.token_urlsafe(18)
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = PhoneVerification(
        challenge_id=challenge_id,
        phone=phone,
        purpose=RESET_PURPOSE,
        name=user.name,
        password_hash="reset-pending",
        code_hash=_hash_code(challenge_id, code),
        attempts=0,
        request_ip=request_ip,
        expires_at=now + timedelta(seconds=OTP_TTL_SECONDS),
        created_at=now,
    )
    db.add(challenge)
    db.flush()
    try:
        _send_reset_otp(phone, code)
    except Exception:
        db.delete(challenge)
        db.flush()
        raise
    return {
        "otp_required": True,
        "challenge_id": challenge_id,
        "expires_in": OTP_TTL_SECONDS,
        "resend_after": RESEND_COOLDOWN_SECONDS,
        "message": "کد بازیابی ارسال شد.",
    }


def reset_password_with_otp(
    db: Session, *, challenge_id: str, code: str, new_password: str
) -> tuple[User, str]:
    code = (code or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not challenge_id or not code.isdigit() or len(code) != OTP_LENGTH:
        raise ValueError("invalid verification code")
    if not isinstance(new_password, str) or len(new_password) < 8:
        raise ValueError("password must contain at least 8 characters")

    challenge = db.scalar(
        select(PhoneVerification)
        .where(
            PhoneVerification.challenge_id == challenge_id,
            PhoneVerification.purpose == RESET_PURPOSE,
        )
        .with_for_update()
    )
    if challenge is None:
        raise ValueError("verification request not found")
    if challenge.verified_at is not None:
        raise ValueError("verification request already used")
    expires = _as_utc(challenge.expires_at)
    if expires is None or expires <= utcnow():
        raise TimeoutError("verification code expired")
    if int(challenge.attempts or 0) >= MAX_ATTEMPTS:
        raise PermissionError("too many verification attempts")

    challenge.attempts = int(challenge.attempts or 0) + 1
    expected = _hash_code(challenge_id, code)
    if not secrets.compare_digest(expected, challenge.code_hash):
        db.flush()
        raise ValueError("incorrect verification code")

    user = db.scalar(select(User).where(User.phone == challenge.phone, User.status == "active").with_for_update())
    if user is None:
        raise ValueError("user not found")

    user.password_hash = hash_password(new_password)
    challenge.verified_at = utcnow()
    revoke_all_sessions(db, user.id)
    token, _ = issue_session(db, user)
    db.flush()
    return user, token


class PasswordResetRequest(BaseModel):
    phone: str = Field(min_length=3, max_length=32)


class PasswordResetConfirmRequest(BaseModel):
    challenge_id: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=6, max_length=8)
    new_password: str = Field(min_length=8, max_length=256)


reset_router = APIRouter(prefix="/auth/password-reset", tags=["auth"])


@reset_router.post("/request")
def password_reset_request(
    req: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        request_ip = request.client.host if request.client else None
        result = request_password_reset_otp(db, phone=req.phone, request_ip=request_ip)
        db.commit()
        return result
    except TimeoutError as exc:
        db.rollback()
        raise HTTPException(status_code=429, detail="لطفاً کمی بعد دوباره تلاش کنید.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="سرویس پیامک موقتاً در دسترس نیست.") from exc


@reset_router.post("/confirm")
def password_reset_confirm(req: PasswordResetConfirmRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        user, token = reset_password_with_otp(
            db,
            challenge_id=req.challenge_id,
            code=req.code,
            new_password=req.new_password,
        )
        db.commit()
        return {
            "token": token,
            "user": {
                "id": user.id,
                "public_id": user.public_id,
                "name": user.name,
                "phone": user.phone,
                "role": user.role,
                "status": user.status,
            },
            "password_reset": True,
        }
    except TimeoutError as exc:
        db.rollback()
        raise HTTPException(status_code=410, detail="کد بازیابی منقضی شده است.") from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=429, detail="تعداد تلاش‌های مجاز تمام شده است.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def attach_router(target_router: APIRouter) -> None:
    target_router.add_api_route(
        "/auth/password-reset/request",
        password_reset_request,
        methods=["POST"],
        response_model=dict[str, object],
        tags=["auth"],
    )
    target_router.add_api_route(
        "/auth/password-reset/confirm",
        password_reset_confirm,
        methods=["POST"],
        response_model=dict[str, object],
        tags=["auth"],
    )
