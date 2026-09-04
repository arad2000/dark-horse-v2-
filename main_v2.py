"""Dark Horse V2 — Liara commercial deploy entrypoint.

Mounts scoring (v2), commercial auth/billing (v1), admin ops, and feedback
collection. Production payment remains fail-closed without explicit approval.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_v2")

# Routers
from admin_router import router as admin_router
from commercial_api import router as commercial_router
from feedback_api import router as feedback_router, legacy_router as feedback_legacy_router

try:
    from darkhorse_api_v2 import router as scoring_router
except Exception as exc:  # pragma: no cover - deploy diagnostics
    scoring_router = None
    logger.exception("scoring router import failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("✅ COMMERCIAL_ROUTER_IMPORTED=%s", commercial_router is not None)
    logger.info("✅ ADMIN_ROUTER_IMPORTED=%s", admin_router is not None)
    logger.info("✅ FEEDBACK_ROUTER_IMPORTED=%s", feedback_router is not None)

    # Operational tables for auth/credits/billing/feedback (not psychometric JSON data).
    try:
        from database import init_db

        import models  # noqa: F401 — user_sessions / user_feedback tables
        import billing_models  # noqa: F401

        init_db()
        logger.info("✅ INIT_DB_OK")
    except Exception as exc:
        logger.exception("init_db failed: %s", exc)

    yield


app = FastAPI(title="Dark Horse V2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if scoring_router is not None:
    app.include_router(scoring_router)
    logger.info("✅ SCORING_ROUTER_MOUNTED")
else:
    logger.warning("⚠️ SCORING_ROUTER_NOT_MOUNTED")

app.include_router(commercial_router)
app.include_router(admin_router)
app.include_router(feedback_router)
app.include_router(feedback_legacy_router)
logger.info("✅ ROUTERS_MOUNTED commercial=/api/v1 admin=/api/v1/admin feedback=/api/v1/feedback legacy=/api/feedback/submit")


@app.get("/")
def root() -> dict:
    return {
        "service": "asbe-siah",
        "status": "ok",
        "commercial_router_mounted": True,
        "admin_router_mounted": True,
        "feedback_router_mounted": True,
        "commercial_prefix": "/api/v1",
        "admin_prefix": "/api/v1/admin",
        "feedback_prefix": "/api/v1/feedback",
        "legacy_feedback_submit": "/api/feedback/submit",
        "commit_hint": "deploy/liara-commercial-sandbox",
    }


@app.get("/__runtime_fingerprint")
def runtime_fingerprint() -> dict:
    return {
        "service": "asbe-siah",
        "commercial_router_mounted": True,
        "admin_router_mounted": True,
        "feedback_router_mounted": True,
        "commercial_prefix": "/api/v1",
        "admin_prefix": "/api/v1/admin",
        "feedback_prefix": "/api/v1/feedback",
        "legacy_feedback_submit": "/api/feedback/submit",
        "billing_free_mode": os.getenv("BILLING_FREE_MODE", "false"),
        "zarinpal_sandbox": os.getenv("ZARINPAL_SANDBOX", "true"),
        "commit_hint": "deploy/liara-commercial-sandbox",
    }
