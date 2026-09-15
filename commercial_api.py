"""Staged commercial API wiring for Dark Horse V2.

This module exposes authentication, phone verification, test-credit, result
persistence, and sandbox billing endpoints without touching scoring/ranking or
enabling PostgreSQL runtime cutover.
"""
from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service import authenticate_user, resolve_session
from billing_api import create_payment_request, handle_payment_callback
from billing_credit_service import consume_one_test, ensure_free_entitlement, is_billing_free_mode
from billing_models import Entitlement, Order, Payment, User
from database import get_db
from phone_verification_service import request_registration_otp, verify_registration_otp
from production_billing_guard import assert_production_billing_configuration

router = APIRouter(prefix="/api/v1", tags=["auth", "credits", "results", "billing"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)


class VerifyRegistrationRequest(BaseModel):
    challenge_id: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=6, max_length=8)


class LoginRequest(BaseModel):
    phone: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)


class SaveResultRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    result_summary: dict = Field(min_length=1)


def _public_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "public_id": user.public_id,
        "name": user.name,
        "phone": user.phone,
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
    assert_production_billing_configuration()
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
    base = os.getenv("FRONTEND_APP_URL", "https://asbe-siah.ir/").strip().rstrip("/")
    return base + "/?" + urlencode({"payment": payment})


@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """Start a verified registration. No user is created before OTP validation."""
    assert_production_billing_configuration()
    try:
        result = request_registration_otp(db, name=req.name, phone=req.phone, password=req.password)
        db.commit()
        return result
    except TimeoutError as exc:
        db.rollback()
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/auth/register/verify")
def verify_register(req: VerifyRegistrationRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    assert_production_billing_configuration()
    try:
        user, token = verify_registration_otp(db, challenge_id=req.challenge_id, code=req.code)
        ensure_free_entitlement(db, user.id)
        db.commit()
        return {
            "token": token,
            "user": _public_user(user),
            "quota": _quota(db, user.id),
            "phone_verified": True,
        }
    except TimeoutError as exc:
        db.rollback()
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    assert_production_billing_configuration()
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
    """Return remaining credits; in free mode top-up first so UI does not paywall."""
    assert_production_billing_configuration()
    if is_billing_free_mode():
        try:
            ensure_free_entitlement(db, user.id)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"credits_remaining": _quota(db, user.id), "user_id": user.id}


@router.post("/me/consume-test")
def consume_test(user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    assert_production_billing_configuration()
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
def save_result(req: SaveResultRequest, user: User = Depends(_current_user)) -> dict[str, object]:
    """Persist the authenticated user's final journey summary exactly once per session."""
    from api_persistence_adapter import OperationalPersistenceAdapter, assert_safe_mode
    from operational_store import OperationalStore

    try:
        assert_safe_mode()
        summary = dict(req.result_summary)
        nested_session_id = summary.get("session_id")
        if nested_session_id is not None and str(nested_session_id) != req.session_id:
            raise ValueError("result_summary session_id does not match session_id")
        summary["session_id"] = req.session_id
        session = OperationalPersistenceAdapter(OperationalStore()).save_result(
            req.session_id,
            int(user.id),
            summary,
        )
        return {
            "saved": True,
            "completed": bool(session.is_completed),
            "session_id": session.session_uuid,
            "operational_session_id": int(session.id),
        }
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        if "exceeds" in str(exc):
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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


@router.get("/billing/sandbox", response_class=HTMLResponse)
def sandbox_payment_page(
    request: Request,
    order_id: str = Query(..., min_length=8, max_length=64),
    authority: str = Query(..., min_length=8, max_length=64),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Browser-testable mock gateway; never available under production billing guard."""
    if _server_billing_provider() != "mock":
        raise HTTPException(status_code=404, detail="sandbox payment page is disabled")

    order = db.scalar(select(Order).where(Order.public_id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="unknown order")
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == order.id,
            Payment.provider == "mock",
            Payment.provider_authority == authority,
        )
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="unknown sandbox payment")

    callback = _callback_url(request)
    success_url = callback + "?" + urlencode({"order_id": order.public_id, "Authority": authority, "Status": "OK"})
    failed_url = callback + "?" + urlencode({"order_id": order.public_id, "Authority": authority, "Status": "NOK"})
    safe_amount = html.escape(f"{int(order.amount_minor):,}")
    safe_order = html.escape(order.public_id)
    safe_authority = html.escape(authority)
    body = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dark Horse Sandbox Payment</title>
<style>body{{font-family:sans-serif;background:#0c0c12;color:#eee;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:18px}}.box{{max-width:430px;width:100%;background:#161622;border:1px solid rgba(212,175,55,.45);border-radius:18px;padding:22px;box-sizing:border-box;text-align:center}}h1{{color:#f0c040;font-size:1.4rem}}.amount{{font-size:2rem;color:#f0c040;font-weight:800;margin:12px 0}}.meta{{color:#aaa;line-height:1.9;font-size:.82rem;word-break:break-word}}a{{display:block;text-decoration:none;padding:13px;border-radius:11px;margin-top:10px;font-weight:700}}.ok{{background:#d4af37;color:#111}}.no{{background:#2b2b3a;color:#eee}}</style></head>
<body><main class="box"><h1>درگاه آزمایشی اسب سیاه</h1><div class="amount">{safe_amount} ریال</div><p>این صفحه فقط برای تست سندباکس است و تراکنش مالی واقعی انجام نمی‌دهد.</p><div class="meta">شماره سفارش: {safe_order}<br>Authority: {safe_authority}</div><a class="ok" href="{html.escape(success_url, quote=True)}">پرداخت موفق آزمایشی</a><a class="no" href="{html.escape(failed_url, quote=True)}">لغو / پرداخت ناموفق</a></main></body></html>"""
    return HTMLResponse(content=body)


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
