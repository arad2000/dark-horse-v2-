"""Staged commercial API wiring for Dark Horse V2.

This module exposes authentication, phone verification, test-credit, result
persistence, and controlled billing endpoints without touching scoring/ranking
or enabling PostgreSQL runtime cutover.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from auth_service import authenticate_user, resolve_session
from billing_api import create_payment_request, handle_payment_callback
from billing_credit_service import consume_one_test, ensure_free_entitlement, is_billing_free_mode
from billing_models import Entitlement, JourneyCreditConsumption, Payment, User
from database import get_db
from models import UserSession
from password_reset_service import attach_router
from phone_verification_service import request_registration_otp, verify_registration_otp
from production_billing_guard import assert_production_billing_configuration

router = APIRouter(prefix="/api/v1", tags=["auth", "credits", "results", "billing"])
attach_router(router)
logger = logging.getLogger("darkhorse.quota")


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


class ConsumeTestRequest(BaseModel):
    """A credit charge is idempotent for exactly one authenticated journey."""
    session_uuid: str = Field(min_length=8, max_length=64)


class SaveResultRequest(BaseModel):
    """Canonical journey identifier shared by discovery, quota and result APIs."""
    session_uuid: str = Field(min_length=8, max_length=64)
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


def _quota_details(db: Session, user_id: int) -> dict[str, int]:
    """Return a server-authoritative quota snapshot."""
    rows = list(
        db.scalars(
            select(Entitlement).where(
                Entitlement.user_id == user_id,
                Entitlement.status == "active",
            )
        )
    )
    remaining = sum(
        int(row.credits_remaining)
        for row in rows
        if int(row.credits_remaining) > 0 and _valid_expiry(row.expires_at)
    )
    consumed = sum(
        max(0, int(row.credits_granted) - int(row.credits_remaining))
        for row in rows
    )
    granted = sum(int(row.credits_granted) for row in rows)
    return {
        "credits_granted": granted,
        "credits_consumed": consumed,
        "credits_remaining": remaining,
    }


def _quota(db: Session, user_id: int) -> int:
    return _quota_details(db, user_id)["credits_remaining"]


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


def _frontend_redirect(payment: str, *, order_id: str | None = None, credits_added: int | None = None) -> str:
    base = os.getenv("FRONTEND_APP_URL", "https://asbe-siah.ir").strip().rstrip("/")
    query: dict[str, str] = {"payment": payment}
    if order_id:
        query["order_id"] = str(order_id)
    if credits_added is not None:
        query["credits_added"] = str(int(credits_added))
    return base + "/?" + urlencode(query)


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
        details = _quota_details(db, user.id)
        return {
            "token": token,
            "user": _public_user(user),
            "quota": details["credits_remaining"],
            "credits_remaining": details["credits_remaining"],
            "credits_consumed": details["credits_consumed"],
            "credits_granted": details["credits_granted"],
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
        details = _quota_details(db, user.id)
        return {
            "token": token,
            "user": _public_user(user),
            "quota": details["credits_remaining"],
            "credits_remaining": details["credits_remaining"],
            "credits_consumed": details["credits_consumed"],
            "credits_granted": details["credits_granted"],
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=401, detail="invalid credentials") from exc


@router.get("/me")
def me(user: User = Depends(_current_user)) -> dict[str, object]:
    return {"user": _public_user(user)}


@router.get("/me/quota")
def quota(user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    """Return a server-authoritative quota snapshot."""
    assert_production_billing_configuration()
    if is_billing_free_mode():
        try:
            ensure_free_entitlement(db, user.id)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return _quota_details(db, user.id)


@router.get("/runtime/quota-health")
def quota_health(db: Session = Depends(get_db)) -> dict[str, object]:
    """Non-sensitive runtime check for deployment and migration verification."""
    expected_revision = "0010_journey_credit_consumptions"
    try:
        ledger_table_exists = bool(db.bind and inspect(db.bind).has_table("journey_credit_consumptions"))
    except Exception:
        ledger_table_exists = False
    try:
        revisions = [str(v) for v in db.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num")).scalars().all()]
    except Exception:
        revisions = []
    return {
        "quota_idempotency": "journey_credit_consumptions_v1",
        "journey_session_autoprovision": True,
        "ledger_table_exists": ledger_table_exists,
        "expected_migration_revision": expected_revision,
        "alembic_revisions": revisions,
        "migration_ok": expected_revision in revisions,
        "postgres_runtime_cutover_approved": os.getenv("POSTGRES_RUNTIME_CUTOVER_APPROVED", "false").strip().lower() in {"1", "true", "yes", "on"},
        "shadow_persistence": os.getenv("DARK_HORSE_SHADOW_PERSISTENCE", "false").strip().lower() in {"1", "true", "yes", "on"},
    }


@router.post("/me/consume-test")
def consume_test(
    req: ConsumeTestRequest,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Charge at most once for the supplied authenticated journey UUID.

    The authenticated user row is locked for the duration of the charge. This
    serializes concurrent retries for an account while the dedicated ledger is
    the per-journey idempotency marker. A missing journey row is provisioned
    for this authenticated user, avoiding a silent 404 when discovery
    persistence did not happen before the result was rendered.
    """
    assert_production_billing_configuration()
    logger.info("quota consume request user_id=%s session_uuid=%s", user.id, req.session_uuid)
    try:
        locked_user = db.scalar(select(User).where(User.id == user.id).with_for_update())
        if locked_user is None:
            raise HTTPException(status_code=401, detail="authenticated user not found")
        user = locked_user

        session_stmt = select(UserSession).where(UserSession.session_uuid == req.session_uuid)
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            session_stmt = session_stmt.with_for_update()
        session = db.scalar(session_stmt)
        if session is None:
            session = UserSession(
                user_id=user.id,
                session_uuid=req.session_uuid,
                micro_motives=[],
                sjt_answers={},
                conjoint_choices={},
            )
            db.add(session)
            db.flush()
        elif session.user_id not in (None, user.id):
            raise HTTPException(status_code=403, detail="journey session does not belong to this user")
        elif session.user_id is None:
            session.user_id = user.id

        existing = db.scalar(
            select(JourneyCreditConsumption).where(
                JourneyCreditConsumption.session_uuid == req.session_uuid,
            )
        )
        if existing is not None:
            if existing.user_id != user.id:
                raise HTTPException(status_code=403, detail="journey session does not belong to this user")
            details = _quota_details(db, user.id)
            db.commit()
            logger.info("quota consume idempotent user_id=%s session_uuid=%s remaining=%s consumed=%s", user.id, req.session_uuid, details["credits_remaining"], details["credits_consumed"])
            return {
                "consumed": 0,
                "already_consumed": True,
                "credits_remaining": details["credits_remaining"],
                "credits_consumed": details["credits_consumed"],
                "credits_granted": details["credits_granted"],
                "session_uuid": req.session_uuid,
                "user": _public_user(user),
            }

        entitlement = consume_one_test(db, user.id)
        db.add(
            JourneyCreditConsumption(
                user_id=user.id,
                session_uuid=req.session_uuid,
                entitlement_id=entitlement.id,
            )
        )
        details = _quota_details(db, user.id)
        db.commit()
        logger.info("quota consume success user_id=%s session_uuid=%s entitlement_id=%s remaining=%s consumed=%s", user.id, req.session_uuid, entitlement.id, details["credits_remaining"], details["credits_consumed"])
        return {
            "consumed": 1,
            "already_consumed": False,
            "credits_remaining": details["credits_remaining"],
            "credits_consumed": details["credits_consumed"],
            "credits_granted": details["credits_granted"],
            "entitlement_id": entitlement.id,
            "session_uuid": req.session_uuid,
            "user": _public_user(user),
        }
    except HTTPException as exc:
        db.rollback()
        logger.warning("quota consume rejected user_id=%s session_uuid=%s status=%s detail=%s", user.id, req.session_uuid, exc.status_code, exc.detail)
        raise
    except ValueError as exc:
        db.rollback()
        logger.exception("quota consume conflict user_id=%s session_uuid=%s detail=%s", user.id, req.session_uuid, exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/me/save-result")
def save_result(req: SaveResultRequest, user: User = Depends(_current_user)) -> dict[str, object]:
    """Persist the authenticated user's final journey summary exactly once per session."""
    from api_persistence_adapter import OperationalPersistenceAdapter, assert_safe_mode
    from operational_store import OperationalStore

    try:
        assert_safe_mode()
        summary = dict(req.result_summary)
        nested_session_uuid = summary.get("session_uuid") or summary.get("session_id")
        if nested_session_uuid is not None and str(nested_session_uuid) != req.session_uuid:
            raise ValueError("result_summary session_uuid does not match session_uuid")
        summary["session_uuid"] = req.session_uuid
        session = OperationalPersistenceAdapter(OperationalStore()).save_result(
            req.session_uuid,
            int(user.id),
            summary,
        )
        return {
            "saved": True,
            "completed": bool(session.is_completed),
            "session_uuid": session.session_uuid,
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
    assert_production_billing_configuration()
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
    order_id: str | None = Query(default=None, alias="order_id"),
    authority: str = Query(..., alias="Authority"),
    status: str | None = Query(default=None, alias="Status"),
    db: Session = Depends(get_db),
):
    try:
        provider = _server_billing_provider()
        resolved_order_id = order_id
        if not resolved_order_id:
            payment = db.scalar(
                select(Payment)
                .where(
                    Payment.provider == provider,
                    Payment.provider_authority == authority,
                )
                .order_by(Payment.id.desc())
            )
            if payment is None:
                raise ValueError("unknown payment authority")
            from billing_models import Order
            resolved_order = db.get(Order, payment.order_id)
            if resolved_order is None:
                raise ValueError("payment order not found")
            resolved_order_id = resolved_order.public_id
        result = handle_payment_callback(
            db,
            order_public_id=resolved_order_id,
            authority=authority,
            status=status,
            provider_name=provider,
            event_key=f"callback:{provider}:{resolved_order_id}:{authority}:{status or ''}",
            raw_callback=dict(request.query_params),
            zarinpal_merchant_id=os.getenv("ZARINPAL_MERCHANT_ID") or None,
        )
        db.commit()
        if result.get("verified"):
            return RedirectResponse(
                url=_frontend_redirect(
                    "success",
                    order_id=resolved_order_id,
                    credits_added=int(result.get("credits_added") or 0),
                ),
                status_code=303,
            )
        return RedirectResponse(
            url=_frontend_redirect("failed", order_id=resolved_order_id, credits_added=0),
            status_code=303,
        )
    except HTTPException:
        db.rollback()
        raise
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc