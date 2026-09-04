"""Staged commercial API wiring for Dark Horse V2.

This module exposes authentication, test-credit, saved-result and sandbox
billing endpoints without touching scoring/ranking or enabling PostgreSQL
runtime cutover.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service import authenticate_user, create_verified_user, resolve_session
from billing_api import create_payment_request, handle_payment_callback
from billing_credit_service import consume_one_test, ensure_free_entitlement
from billing_models import Entitlement, RegistrationChallenge, SavedResult, User
from database import get_db
from otp_service import create_registration_challenge, send_code, verify_registration_challenge

router = APIRouter(prefix="/api/v1", tags=["auth", "credits", "billing"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(pattern=r"^09\d{9}$")
    password: str = Field(min_length=8, max_length=256)


class VerifyRegistrationRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=36)
    code: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    phone: str = Field(pattern=r"^09\d{9}$")
    password: str = Field(min_length=8, max_length=256)


class SaveResultRequest(BaseModel):
    result_summary: dict = Field(default_factory=dict)
    session_uuid: str | None = Field(default=None, min_length=1, max_length=36)


def _public_user(user: User) -> dict[str, object]:
    return {
        "public_id": user.public_id,
        "name": user.name,
        "role": user.role,
        "status": user.status,
    }


def _valid_expiry(value: datetime | None) -> bool:
    if value is None:
        return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value > datetime.now(timezone.utc)


def _quota(db: Session, user_id: int) -> int:
    rows = db.scalars(
        select(Entitlement).where(
            Entitlement.user_id == user_id,
            Entitlement.status == "active",
            Entitlement.credits_remaining > 0,
        )
    )
    return sum(int(row.credits_remaining) for row in rows if _valid_expiry(row.expires_at))


def _current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        return resolve_session(db, token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _server_billing_provider() -> str:
    provider = os.getenv("BILLING_PROVIDER", "mock").strip().lower()
    if provider not in {"mock", "zarinpal"}:
        raise HTTPException(status_code=503, detail="billing provider is misconfigured")
    if provider == "zarinpal":
        sandbox = os.getenv("ZARINPAL_SANDBOX", "false").strip().lower() in {"1", "true", "yes", "on"}
        production_approved = os.getenv("ZARINPAL_PRODUCTION_APPROVED", "false").strip().lower() in {"1", "true", "yes", "on"}
        if not sandbox and not production_approved:
            raise HTTPException(status_code=503, detail="live ZarinPal requires explicit production approval")
    return provider


def _callback_url(request: Request) -> str:
    configured = os.getenv("BILLING_CALLBACK_URL", "").strip()
    if configured:
        return configured
    return str(request.base_url).rstrip("/") + "/api/v1/billing/callback"


def _frontend_redirect(payment: str) -> str:
    base = os.getenv("FRONTEND_APP_URL", "https://arad2000.github.io/dark-horse-v2-/").strip().rstrip("/")
    return base + "/?" + urlencode({"payment": payment})


@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """Start registration and persist only a verification challenge until OTP succeeds."""
    try:
        row, code = create_registration_challenge(db, name=req.name, phone=req.phone, password=req.password)
        send_code(row.phone, code)
        db.commit()
        response = {"challenge_id": row.challenge_id, "expires_in": max(0, int((row.expires_at - datetime.now(timezone.utc)).total_seconds()))}
        # Test/staging can opt into returning the mock code. Production should not.
        if os.getenv("OTP_EXPOSE_DEBUG_CODE", "false").strip().lower() in {"1", "true", "yes", "on"}:
            response["debug_code"] = code
        return response
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/auth/register/verify")
def verify_registration(req: VerifyRegistrationRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        challenge = verify_registration_challenge(db, challenge_id=req.challenge_id, code=req.code)
        user, token = create_verified_user(
            db,
            name=challenge.name,
            phone=challenge.phone,
            password_hash=challenge.password_hash,
        )
        ensure_free_entitlement(db, user.id)
        db.commit()
        return {"token": token, "user": _public_user(user), "quota": _quota(db, user.id)}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        user, token = authenticate_user(db, phone=req.phone, password=req.password)
        ensure_free_entitlement(db, user.id)
        db.commit()
        return {"token": token, "user": _public_user(user), "quota": _quota(db, user.id)}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=401, detail="invalid credentials") from exc


@router.get("/me")
def me(user: User = Depends(_current_user)) -> dict[str, object]:
    return {"user": _public_user(user)}


@router.get("/me/quota")
def quota(user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    return {"credits_remaining": _quota(db, user.id), "user_id": user.id}


@router.post("/me/consume-test")
def consume_test(user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        entitlement = consume_one_test(db, user.id)
        remaining = _quota(db, user.id)
        db.commit()
        return {
            "consumed": 1,
            "credits_remaining": remaining,
            "entitlement_id": entitlement.id,
            "user": _public_user(user),
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/me/save-result")
def save_result(req: SaveResultRequest, user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        row = SavedResult(user_id=user.id, session_uuid=req.session_uuid, result_summary=req.result_summary)
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"saved": True, "result_id": row.id}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="ذخیره نتیجه ناموفق بود") from exc


@router.post("/billing/create-payment")
def create_payment(request: Request, user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        provider = _server_billing_provider()
        result = create_payment_request(
            db,
            user_id=user.id,
            callback_url=_callback_url(request),
            provider_name=provider,
            zarinpal_merchant_id=os.getenv("ZARINPAL_MERCHANT_ID") or None,
        )
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/billing/callback")
def billing_callback(
    request: Request,
    order_id: str = Query(..., alias="order_id"),
    authority: str = Query(..., alias="Authority"),
    status: str | None = Query(default=None, alias="Status"),
    db: Session = Depends(get_db),
):
    try:
        provider = _server_billing_provider()
        result = handle_payment_callback(
            db,
            order_public_id=order_id,
            authority=authority,
            status=status,
            provider_name=provider,
            event_key=f"callback:{provider}:{order_id}:{authority}:{status or ''}",
            raw_callback=dict(request.query_params),
            zarinpal_merchant_id=os.getenv("ZARINPAL_MERCHANT_ID") or None,
        )
        db.commit()
        if result.get("verified"):
            return RedirectResponse(url=_frontend_redirect("success"), status_code=303)
        return RedirectResponse(url=_frontend_redirect("failed"), status_code=303)
    except HTTPException:
        db.rollback()
        raise
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
