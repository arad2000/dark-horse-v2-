"""Staged commercial API wiring for Dark Horse V2.

This module exposes authentication, phone verification, test-credit, saved-result and sandbox
billing endpoints without touching scoring/ranking or enabling PostgreSQL runtime cutover.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, case, func, inspect, or_, select, text
from sqlalchemy.orm import Session

from auth_service import authenticate_user, create_verified_user, resolve_session
from billing_api import create_payment_request, handle_payment_callback
from billing_credit_service import consume_one_test, ensure_free_entitlement
from billing_models import Entitlement, RegistrationChallenge, SavedResult, User, JourneyCreditConsumption
from database import get_db
from otp_service import create_registration_challenge, send_code, verify_registration_challenge
from models import UserSession

router = APIRouter(prefix="/api/v1", tags=["auth", "credits", "billing"])
logger = logging.getLogger("darkhorse.quota")

MAX_SAVED_RESULT_BYTES = 64 * 1024


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


class ConsumeTestRequest(BaseModel):
    """A credit charge is idempotent for exactly one authenticated journey UUID."""
    session_uuid: str = Field(min_length=8, max_length=64)


class SaveResultRequest(BaseModel):
    result_summary: dict = Field(default_factory=dict)
    session_uuid: str | None = Field(default=None, min_length=1, max_length=36)

    @field_validator("result_summary")
    @classmethod
    def validate_result_summary(cls, value: dict) -> dict:
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("result_summary must contain JSON-compatible values") from exc
        if len(encoded) > MAX_SAVED_RESULT_BYTES:
            raise ValueError("result_summary is too large")
        return value


def _public_user(user: User) -> dict[str, object]:
    return {"public_id": user.public_id, "name": user.name, "role": user.role, "status": user.status}


def _valid_expiry(value: datetime | None) -> bool:
    if value is None:
        return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value > datetime.now(timezone.utc)


def _quota_details(db: Session, user_id: int) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    consumed_expr = case(
        (Entitlement.credits_granted > Entitlement.credits_remaining,
         Entitlement.credits_granted - Entitlement.credits_remaining),
        else_=0,
    )
    remaining_expr = case(
        (
            and_(
                Entitlement.credits_remaining > 0,
                or_(Entitlement.expires_at.is_(None), Entitlement.expires_at > now),
            ),
            Entitlement.credits_remaining,
        ),
        else_=0,
    )
    row = db.execute(
        select(
            func.coalesce(func.sum(Entitlement.credits_granted), 0),
            func.coalesce(func.sum(consumed_expr), 0),
            func.coalesce(func.sum(remaining_expr), 0),
        ).where(
            Entitlement.user_id == user_id,
            Entitlement.status == "active",
        )
    ).one()
    granted, consumed, remaining = (int(value or 0) for value in row)
    return {
        "credits_granted": granted,
        "credits_consumed": consumed,
        "credits_remaining": remaining,
    }


def _quota(db: Session, user_id: int) -> int:
    return _quota_details(db, user_id)["credits_remaining"]


def _current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
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
    try:
        row, code = create_registration_challenge(db, name=req.name, phone=req.phone, password=req.password)
        send_code(row.phone, code)
        db.commit()
        response = {"challenge_id": row.challenge_id, "expires_in": max(0, int((row.expires_at - datetime.now(timezone.utc)).total_seconds()))}
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
        user, token = create_verified_user(db, name=challenge.name, phone=challenge.phone, password_hash=challenge.password_hash)
        ensure_free_entitlement(db, user.id)
        db.commit()
        details = _quota_details(db, user.id)
        return {"token": token, "user": _public_user(user), "quota": details["credits_remaining"], **details}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        user, token = authenticate_user(db, phone=req.phone, password=req.password)
        ensure_free_entitlement(db, user.id)
        db.commit()
        details = _quota_details(db, user.id)
        return {"token": token, "user": _public_user(user), "quota": details["credits_remaining"], **details}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=401, detail="invalid credentials") from exc


@router.get("/me")
def me(user: User = Depends(_current_user)) -> dict[str, object]:
    return {"user": _public_user(user)}


@router.get("/me/quota")
def quota(user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    return _quota_details(db, user.id)


@router.get("/runtime/quota-health")
def quota_health(db: Session = Depends(get_db)) -> dict[str, object]:
    """Non-sensitive runtime check for deployment and migration verification."""
    expected_revision = "0009_journey_credit_consumptions"
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
def consume_test(req: ConsumeTestRequest, user: User = Depends(_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    """Charge at most once for an authenticated journey UUID.

    An already-consumed journey takes a read-only idempotent fast-path. A new
    charge locks the authenticated user for the transaction; the dedicated
    billing ledger remains the per-journey idempotency marker. A missing journey
    row is provisioned for this authenticated user, so charging cannot silently
    fail solely because discovery persistence was unavailable.
    """
    logger.info("quota consume request user_id=%s session_uuid=%s", user.id, req.session_uuid)
    try:
        existing = db.scalar(
            select(JourneyCreditConsumption).where(JourneyCreditConsumption.session_uuid == req.session_uuid)
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
                "credits_granted": details["credits_granted"],
                "credits_consumed": details["credits_consumed"],
                "session_uuid": req.session_uuid,
                "user": _public_user(user),
            }

        locked_user = db.scalar(select(User).where(User.id == user.id).with_for_update())
        if locked_user is None:
            raise HTTPException(status_code=401, detail="authenticated user not found")
        user = locked_user

        session_stmt = select(UserSession).where(UserSession.session_uuid == req.session_uuid).with_for_update()
        session = db.scalar(session_stmt)
        session_provisioned = False
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
            session_provisioned = True
        elif session.user_id not in (None, user.id):
            raise HTTPException(status_code=403, detail="journey session does not belong to this user")
        elif session.user_id is None:
            session.user_id = user.id

        entitlement = consume_one_test(db, user.id)
        db.add(JourneyCreditConsumption(user_id=user.id, session_uuid=req.session_uuid, entitlement_id=entitlement.id))
        # Billing confirms completion only for a real pre-existing journey.
        # Auto-provisioned sessions are placeholders and must retain their
        # independent lifecycle state until the journey itself completes.
        if not session_provisioned:
            session.is_completed = True
        details = _quota_details(db, user.id)
        db.commit()
        logger.info("quota consume success user_id=%s session_uuid=%s entitlement_id=%s remaining=%s consumed=%s", user.id, req.session_uuid, entitlement.id, details["credits_remaining"], details["credits_consumed"])
        return {
            "consumed": 1,
            "already_consumed": False,
            "credits_remaining": details["credits_remaining"],
            "credits_granted": details["credits_granted"],
            "credits_consumed": details["credits_consumed"],
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
        result = create_payment_request(db, user_id=user.id, callback_url=_callback_url(request), provider_name=provider, zarinpal_merchant_id=os.getenv("ZARINPAL_MERCHANT_ID") or None)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/billing/callback")
def billing_callback(request: Request, order_id: str = Query(..., alias="order_id"), authority: str = Query(..., alias="Authority"), status: str | None = Query(default=None, alias="Status"), db: Session = Depends(get_db)):
    try:
        provider = _server_billing_provider()
        result = handle_payment_callback(db, order_public_id=order_id, authority=authority, status=status, provider_name=provider, event_key=f"callback:{provider}:{order_id}:{authority}:{status or ''}", raw_callback=dict(request.query_params), zarinpal_merchant_id=os.getenv("ZARINPAL_MERCHANT_ID") or None)
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