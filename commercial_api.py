"""Staged commercial API wiring for Dark Horse V2.

This module exposes authentication and credit-account endpoints without touching
scoring/ranking or enabling PostgreSQL runtime cutover. It is intentionally
small and server-authoritative: plan, credit balances, and payment state are
never accepted from the client as trusted values.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service import authenticate_user, register_user, resolve_session
from billing_credit_service import consume_one_test, ensure_free_entitlement
from billing_models import Entitlement, User
from database import get_db

router = APIRouter(prefix="/api/v1", tags=["auth", "credits"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    phone: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)


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


@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        user, token = register_user(db, name=req.name, phone=req.phone, password=req.password)
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
