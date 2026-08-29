"""Standalone protected Admin HTTP API for staged validation.

This app is deliberately NOT mounted by main_v2.py. It provides a real FastAPI
surface over admin_service so the RBAC/audit contract can be tested before any
production wiring or deployment.
"""
from __future__ import annotations

from contextlib import contextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from admin_api import admin_grant_credits, admin_revoke_entitlement, dashboard_summary
from auth_service import resolve_session
from database import SessionLocal

app = FastAPI(title="Dark Horse Admin API (staged)", version="0.1")


@contextmanager
def db_session():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_admin(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        with db_session() as db:
            user = resolve_session(db, token)
            if user.role not in {"admin", "support"}:
                raise HTTPException(status_code=403, detail="admin access required")
            return user.id
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


class GrantRequest(BaseModel):
    user_id: int
    plan_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=1000)


class RevokeRequest(BaseModel):
    entitlement_id: int
    reason: str = Field(min_length=1, max_length=1000)


@app.get("/api/v1/admin/dashboard")
def get_dashboard(admin_user_id: int = Depends(current_admin)):
    with db_session() as db:
        actor = db.get(__import__("billing_models").User, admin_user_id)
        try:
            return dashboard_summary(db, actor)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/v1/admin/credits/grant")
def grant(req: GrantRequest, admin_user_id: int = Depends(current_admin)):
    with db_session() as db:
        actor = db.get(__import__("billing_models").User, admin_user_id)
        try:
            result = admin_grant_credits(
                db,
                actor,
                user_id=req.user_id,
                plan_code=req.plan_code,
                reason=req.reason,
            )
            db.commit()
            return result
        except PermissionError as exc:
            db.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/admin/entitlements/revoke")
def revoke(req: RevokeRequest, admin_user_id: int = Depends(current_admin)):
    with db_session() as db:
        actor = db.get(__import__("billing_models").User, admin_user_id)
        try:
            result = admin_revoke_entitlement(
                db,
                actor,
                entitlement_id=req.entitlement_id,
                reason=req.reason,
            )
            db.commit()
            return result
        except PermissionError as exc:
            db.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
